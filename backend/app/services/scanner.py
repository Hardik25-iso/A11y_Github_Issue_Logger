import asyncio
import base64
import os
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import log_error, log_warning
from backend.app.core.security import validate_resolved_public_url
from backend.app.models import ScanIssue, ScanResponse
from backend.app.services.browser import BrowserUnavailable, browser_session, ensure_remote_driver, remote_mode

# Cap how many element screenshots we capture per scan to bound response size
# and scan time. The most severe violations come first after normalization.
MAX_SCREENSHOTS = 10
# Hard ceiling per element screenshot, whatever Playwright's own timeouts do.
SCREENSHOT_CAP_SECONDS = 5

# Max concurrent live browser scans — prevents resource exhaustion. Read
# straight from the environment because it is fixed at import time; set it to
# the hosted browser plan's concurrency (1 on the Browserless free tier).
_SCAN_SEMAPHORE = asyncio.Semaphore(int(os.getenv("BROWSER_MAX_CONCURRENCY", "3")))

# A remote scan that hit a disconnect is retried only if this much of the
# total budget remains; the retry opens a new, separately billed connection.
RETRY_MIN_SECONDS = 15

# Honest, specific reasons for each way the remote browser can be unavailable.
BROWSER_NOTICES = {
    "quota": "The free live-scan quota is used up; try again later.",
    "auth": "Live scanning is misconfigured on the server.",
    "connect": "The remote browser could not be reached.",
    "disconnected": "The remote browser disconnected during the scan.",
    "timeout": "The live scan took too long.",
}

SEVERITY_MAP = {
    "critical": "Critical",
    "serious": "High",
    "moderate": "Medium",
    "minor": "Low",
}

WCAG_URLS = {
    "1.1.1": "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html",
    "1.3.1": "https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html",
    "2.4.4": "https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html",
    "4.1.2": "https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html",
}

BLOCKED_RESOURCE_TYPES = {"font", "image", "media"}

# Substrings that suggest a scan was redirected to a login/auth wall, so we can
# warn that results may reflect the login screen rather than the intended page.
LOGIN_INDICATORS = ("login", "signin", "sign-in", "/auth", "sso", "oauth", "accounts.")

def _criterion(tags: list[str]) -> str:
    for tag in tags:
        digits = tag[4:]
        if tag.startswith("wcag") and len(digits) >= 3 and digits.isdigit():
            if len(digits) == 3:
                return f"{digits[0]}.{digits[1]}.{digits[2]}"
            return f"{digits[0]}.{digits[1]}.{digits[2:]}"
    return "4.1.2"


def _wcag_url(criterion: str, fallback: str) -> str:
    return WCAG_URLS.get(criterion, fallback)


def _summary(issues: list[ScanIssue]) -> dict[str, int]:
    return {
        severity: sum(issue.severity == severity for issue in issues)
        for severity in ("Critical", "High", "Medium", "Low")
    }


def fallback_scan(url: str, notice: str | None = None) -> ScanResponse:
    issues = [
        ScanIssue(
            id="image-alt",
            title="Images must have alternative text",
            severity="Critical",
            wcag_criterion="1.1.1",
            wcag_url=WCAG_URLS["1.1.1"],
            element='<img src="/hero-product.jpg">',
            selector="main .hero img",
            impact="Screen reader users cannot understand the purpose of the featured image.",
            description="The image does not have an alt attribute or an equivalent accessible name.",
            occurrences=2,
            tags=["accessibility", "wcag-1.1.1", "images"],
        ),
        ScanIssue(
            id="button-name",
            title="Buttons must have discernible text",
            severity="High",
            wcag_criterion="4.1.2",
            wcag_url=WCAG_URLS["4.1.2"],
            element='<button class="search-icon"></button>',
            selector="header button.search-icon",
            impact="Screen reader users hear an unnamed button and cannot determine its action.",
            description="The icon-only button has no visible text, aria-label, or accessible name.",
            occurrences=1,
            tags=["accessibility", "wcag-4.1.2", "aria", "buttons"],
        ),
        ScanIssue(
            id="link-name",
            title="Links must have discernible text",
            severity="Medium",
            wcag_criterion="2.4.4",
            wcag_url=WCAG_URLS["2.4.4"],
            element='<a href="/account"><svg>...</svg></a>',
            selector="nav a.account-link",
            impact="Keyboard and screen reader users cannot identify the link destination.",
            description="The link contains an unlabeled icon and has no accessible name.",
            occurrences=3,
            tags=["accessibility", "wcag-2.4.4", "links", "navigation"],
        ),
    ]
    return ScanResponse(
        url=url,
        issues=issues,
        summary=_summary(issues),
        source="fallback",
        notice=notice or "Demo results shown. Enable live scanning to audit the requested page.",
    )


def _node_selector(nodes: list[dict]) -> str:
    raw_target = nodes[0].get("target", []) if nodes else []
    # axe-core uses nested lists for elements inside iframes; flatten to strings
    flat_target = [
        part
        for item in raw_target
        for part in (item if isinstance(item, list) else [item])
    ]
    return " ".join(str(p) for p in flat_target) if flat_target else ""


def normalize_violations(violations: list[dict]) -> list[ScanIssue]:
    issues = []
    for violation in violations:
        tags = violation.get("tags", [])
        criterion = _criterion(tags)
        nodes = violation.get("nodes", [])
        issues.append(
            ScanIssue(
                id=violation.get("id", "axe-violation"),
                title=violation.get("help", "Accessibility violation"),
                severity=SEVERITY_MAP.get(violation.get("impact"), "Low"),  # type: ignore[arg-type]
                wcag_criterion=criterion,
                wcag_url=_wcag_url(criterion, violation.get("helpUrl", "")),
                element=nodes[0].get("html", "")[:300] if nodes else "",
                selector=_node_selector(nodes),
                impact=violation.get("description", ""),
                description=violation.get("help", ""),
                occurrences=max(1, len(nodes)),
                tags=tags,
                screenshot=violation.get("screenshot"),
            )
        )
    return issues


async def _capture_element_screenshot(page: Any, selector: str) -> str | None:
    """Screenshot the offending element with a red highlight, as a base64 PNG
    data URI. Returns None on any failure — a missing screenshot must never
    block a scan or fabricate evidence."""
    if not selector:
        return None
    try:
        return await asyncio.wait_for(_highlighted_png(page, selector), SCREENSHOT_CAP_SECONDS)
    except Exception as exc:
        log_warning(f"Screenshot capture skipped for selector {selector!r}: {type(exc).__name__}")
        return None


async def _highlighted_png(page: Any, selector: str) -> str | None:
    locator = page.locator(selector).first
    # An invisible element has nothing to show, and locator.screenshot() on
    # one ignores its own timeout and blocks for Playwright's 30 s default.
    if not await locator.is_visible():
        return None
    await locator.scroll_into_view_if_needed(timeout=2000)
    # Inset box-shadow stays within the element's box, so it is always
    # included in the element screenshot (unlike outline, which can clip).
    await locator.evaluate("el => { el.style.boxShadow = 'inset 0 0 0 3px #ff3b3b'; }")
    png_bytes = await locator.screenshot(timeout=3000)
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def axe_script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "axe.min.js"


async def _guarded_route(route: Any) -> None:
    request = route.request
    try:
        validate_resolved_public_url(request.url)
        if get_settings().block_heavy_scan_resources and request.resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return
    except Exception:
        await route.abort()
        return
    await route.continue_()


async def _run_axe(url: str, axe_path: Path, storage_state: dict | None = None) -> tuple[list[dict], str]:
    """Run axe-core against url in a fresh context. Returns the violations and
    the final URL (post-redirect) so callers can detect a login-wall redirect."""
    settings = get_settings()

    async with browser_session() as browser:
        # storage_state injects the caller's session (cookies/localStorage) for
        # this scan only; the context is discarded immediately afterwards.
        context = await browser.new_context(storage_state=storage_state)
        try:
            page = await context.new_page()
            await page.route("**/*", _guarded_route)
            await page.goto(url, wait_until="domcontentloaded", timeout=settings.scan_timeout_ms)
            validate_resolved_public_url(page.url)
            final_url = page.url
            await page.add_script_tag(path=str(axe_path))
            # Return only the violations: the full result (passes, incomplete,
            # inapplicable, each with node HTML) is often 1 MB+, and moving it
            # into Python dominated scan time on a 0.1-CPU host.
            violations = await page.evaluate("async () => (await axe.run(document)).violations || []")
            for violation in violations[:MAX_SCREENSHOTS]:
                selector = _node_selector(violation.get("nodes", []))
                violation["screenshot"] = await _capture_element_screenshot(page, selector)
            return violations, final_url
        finally:
            await context.close()


async def _run_axe_bounded(url: str, axe_path: Path, storage_state: dict | None) -> tuple[list[dict], str]:
    """Local scans run as before. Remote scans are capped at
    SCAN_TOTAL_TIMEOUT_S (staying inside one billed unit) and retried once
    after a mid-scan disconnect if enough of that budget remains."""
    if not remote_mode():
        return await _run_axe(url, axe_path, storage_state)

    # The budget covers browser time only; a driver still starting after a
    # cold boot is waited for first, outside the budget.
    await ensure_remote_driver()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + get_settings().scan_total_timeout_s
    try:
        try:
            return await asyncio.wait_for(_run_axe(url, axe_path, storage_state), deadline - loop.time())
        except BrowserUnavailable as exc:
            if exc.kind != "disconnected" or deadline - loop.time() < RETRY_MIN_SECONDS:
                raise
            log_warning(f"Retrying scan after remote browser disconnect for url={url}")
            return await asyncio.wait_for(_run_axe(url, axe_path, storage_state), deadline - loop.time())
    except TimeoutError:
        raise BrowserUnavailable("timeout") from None


def _looks_like_login_wall(requested_url: str, final_url: str) -> bool:
    if final_url == requested_url:
        return False
    lowered = final_url.lower()
    return any(indicator in lowered for indicator in LOGIN_INDICATORS)


async def scan_url(url: str, storage_state: dict | None = None) -> ScanResponse:
    settings = get_settings()
    if not settings.enable_live_scan:
        return fallback_scan(url)

    try:
        validate_resolved_public_url(url)
        axe_path = axe_script_path()
        if not axe_path.exists():
            return fallback_scan(url, "Local axe-core bundle is missing; demo results shown.")

        async with _SCAN_SEMAPHORE:
            violations, final_url = await _run_axe_bounded(url, axe_path, storage_state)

        issues = normalize_violations(violations)
        notice = None
        if _looks_like_login_wall(url, final_url):
            notice = (
                "The page redirected to what looks like a login screen, so these "
                "results may reflect the login page rather than the intended page. "
                "Provide a valid session (storage state) to scan authenticated content."
            )
        return ScanResponse(url=url, issues=issues, summary=_summary(issues), source="live", notice=notice)
    except BrowserUnavailable as exc:
        log_warning(f"Live scan unavailable for url={url}: remote browser {exc.kind}")
        return fallback_scan(url, f"Live scan unavailable; demo results shown. {BROWSER_NOTICES[exc.kind]}")
    except Exception as exc:
        log_error(f"Live scan failed for url={url}: {type(exc).__name__}: {exc}", exc=exc)
        return fallback_scan(url, f"Live scan failed; demo results shown. {type(exc).__name__}")
