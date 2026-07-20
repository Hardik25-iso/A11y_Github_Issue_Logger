"""Form-based login capture for authenticated scanning.

Opens a login page in the shared headless browser, submits user-provided
credentials once, and returns only the resulting session storage_state plus a
full-page screenshot as proof of login. Credentials never leave this module:
they are not persisted, not logged, and not included in any response or error.

Supported: simple username/password form logins. Out of scope by design:
SSO/OAuth, MFA/2FA, and CAPTCHA-gated logins.
"""

import base64
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import log_info, log_warning
from backend.app.core.security import validate_resolved_public_url
from backend.app.models import LoginResponse, LoginSelectors
from backend.app.services.scanner import _SCAN_SEMAPHORE, LOGIN_INDICATORS, _acquire_browser

# Auto-detection candidates, tried in order. Callers can override any of them
# via LoginSelectors when detection fails on an unusual form.
USERNAME_SELECTOR_CANDIDATES = (
    "input[type=email]",
    "input[name=username]",
    "input[name=email]",
    "input[name*=user]",
    "input[name*=login]",
    "input[autocomplete=username]",
    "input[type=text]",
)
PASSWORD_SELECTOR = "input[type=password]"
SUBMIT_SELECTOR_CANDIDATES = (
    "button[type=submit]",
    "input[type=submit]",
    "form button",
)

_DISABLED_NOTICE = (
    "Live scanning is disabled (ENABLE_LIVE_SCAN=false), so a real login cannot "
    "be performed. Enable live scanning to use authenticated scans."
)
_UNSUPPORTED_NOTE = (
    "Only simple username/password form logins are supported — SSO/OAuth, "
    "MFA/2FA, and CAPTCHA-protected logins are not."
)


async def _ssrf_route(route: Any) -> None:
    """Abort any request from the login page that targets a non-public address.
    Resource types are not blocked here (unlike the scan route guard) so the
    proof screenshot faithfully shows the page the user logged in to."""
    try:
        validate_resolved_public_url(route.request.url)
    except Exception:
        await route.abort()
        return
    await route.continue_()


async def _first_visible(page: Any, candidates: tuple[str, ...]) -> Any | None:
    for selector in candidates:
        locator = page.locator(selector).first
        try:
            if await locator.count() and await locator.is_visible():
                return locator
        except Exception:
            continue
    return None


def _failure(notice: str, final_url: str = "") -> LoginResponse:
    return LoginResponse(success=False, source="live", final_url=final_url, notice=notice)


async def login_and_capture_session(
    login_url: str,
    username: str,
    password: str,
    selectors: LoginSelectors | None = None,
) -> LoginResponse:
    settings = get_settings()
    if not settings.enable_live_scan:
        return LoginResponse(success=False, source="fallback", notice=_DISABLED_NOTICE)

    overrides = selectors or LoginSelectors()
    try:
        validate_resolved_public_url(login_url)
        async with _SCAN_SEMAPHORE:
            browser, own_browser = await _acquire_browser()
            try:
                # Fresh context per login; discarded below so nothing outlives
                # the request except the returned storage_state.
                context = await browser.new_context()
                try:
                    return await _perform_login(context, login_url, username, password, overrides, settings)
                finally:
                    await context.close()
            finally:
                if own_browser:
                    await browser.close()
    except Exception as exc:
        # Only the exception type is reported: Playwright error strings can
        # embed page content or filled values, and credentials must never
        # reach logs or responses.
        log_warning(f"Login attempt failed for url={login_url}: {type(exc).__name__}")
        return _failure(
            f"The login attempt failed ({type(exc).__name__}). Check that the login URL "
            f"is reachable and shows a standard login form. {_UNSUPPORTED_NOTE}"
        )


async def _perform_login(
    context: Any,
    login_url: str,
    username: str,
    password: str,
    overrides: LoginSelectors,
    settings: Any,
) -> LoginResponse:
    page = await context.new_page()
    await page.route("**/*", _ssrf_route)
    await page.goto(login_url, wait_until="domcontentloaded", timeout=settings.scan_timeout_ms)
    validate_resolved_public_url(page.url)

    if overrides.username:
        username_field = page.locator(overrides.username).first
        if not await username_field.count():
            return _failure(
                f"No element matches the custom username selector {overrides.username!r}.", page.url
            )
    else:
        username_field = await _first_visible(page, USERNAME_SELECTOR_CANDIDATES)
        if username_field is None:
            return _failure(
                f"Could not find a username/email field on the login page. If the form is "
                f"unusual, provide custom selectors. {_UNSUPPORTED_NOTE}",
                page.url,
            )

    password_selector = overrides.password or PASSWORD_SELECTOR
    password_field = page.locator(password_selector).first
    if not await password_field.count():
        return _failure(
            f"Could not find a password field on the login page. If the form is "
            f"unusual, provide custom selectors. {_UNSUPPORTED_NOTE}",
            page.url,
        )

    await username_field.fill(username)
    await password_field.fill(password)

    if overrides.submit:
        submit = page.locator(overrides.submit).first
        submit = submit if await submit.count() else None
    else:
        submit = await _first_visible(page, SUBMIT_SELECTOR_CANDIDATES)

    # SPA logins may not trigger a full navigation, so a navigation timeout is
    # not a failure by itself — success is judged by the resulting page state.
    try:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=settings.scan_timeout_ms):
            if submit is not None:
                await submit.click()
            else:
                await password_field.press("Enter")
    except Exception:
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass

    final_url = page.url
    validate_resolved_public_url(final_url)

    # Honest verification: if a password field is still visible, we are still
    # on a login wall — never report that as a successful login. Checking
    # visibility (not just presence) matters because many signed-in pages
    # still keep a login form in the DOM (nav dropdown, collapsed modal),
    # which would otherwise read as a false "login failed".
    if await _first_visible(page, (password_selector,)) is not None:
        log_info(f"Login rejected by target site for url={login_url}")
        return _failure(
            "The page still shows a login form after submitting, so the login did not "
            f"succeed. Check the credentials and selectors. {_UNSUPPORTED_NOTE}",
            final_url,
        )

    storage_state = await context.storage_state()
    png_bytes = await page.screenshot(full_page=True, timeout=10000)
    screenshot = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")

    notice = None
    if any(indicator in final_url.lower() for indicator in LOGIN_INDICATORS):
        notice = (
            "The post-login URL still looks like an auth page. The session was "
            "captured, but verify the screenshot shows the signed-in page."
        )
    log_info(f"Login captured session for url={login_url} final_url={final_url}")
    return LoginResponse(
        success=True,
        storage_state=storage_state,
        screenshot=screenshot,
        final_url=final_url,
        source="live",
        notice=notice,
    )
