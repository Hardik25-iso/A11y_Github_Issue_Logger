import asyncio
import base64
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import log_error, log_info, log_warning
from backend.app.core.security import validate_resolved_public_url
from backend.app.models import ScanIssue, ScanResponse

# Cap how many element screenshots we capture per scan to bound response size
# and scan time. The most severe violations come first after normalization.
MAX_SCREENSHOTS = 10

# Max concurrent live browser scans — prevents resource exhaustion
_SCAN_SEMAPHORE = asyncio.Semaphore(3)

# Warm browser shared across requests — contexts are isolated per scan
_pw_instance: Any = None
_browser: Any = None

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

_PW_MOD = "playwright.async_api"


async def init_browser_pool() -> None:
    global _pw_instance, _browser
    if not get_settings().enable_live_scan:
        return
    try:
        import importlib
        _pw = importlib.import_module(_PW_MOD)
        _pw_instance = await _pw.async_playwright().start()
        _browser = await _pw_instance.chromium.launch()
        log_info("Browser pool initialised")
    except Exception as exc:
        log_error(f"Browser pool init failed: {exc}", exc=exc)


async def close_browser_pool() -> None:
    global _pw_instance, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _pw_instance:
        await _pw_instance.stop()
        _pw_instance = None
        log_info("Browser pool closed")


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
        locator = page.locator(selector).first
        await locator.scroll_into_view_if_needed(timeout=2000)
        # Inset box-shadow stays within the element's box, so it is always
        # included in the element screenshot (unlike outline, which can clip).
        await locator.evaluate("el => { el.style.boxShadow = 'inset 0 0 0 3px #ff3b3b'; }")
        png_bytes = await locator.screenshot(timeout=3000)
        return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    except Exception as exc:
        log_warning(f"Screenshot capture skipped for selector {selector!r}: {type(exc).__name__}")
        return None


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


async def _acquire_browser() -> tuple[Any, bool]:
    """Return (browser, own_browser). Reuses the warm shared browser when the
    pool is initialised, otherwise launches a fresh one the caller must close."""
    global _browser
    if _browser is None or not _browser.is_connected():
        import importlib
        _pw = importlib.import_module(_PW_MOD)
        pw = await _pw.async_playwright().start()
        browser = await pw.chromium.launch()
        return browser, True
    return _browser, False


async def _run_axe(url: str, axe_path: Path, storage_state: dict | None = None) -> tuple[list[dict], str]:
    """Run axe-core against url, reusing the warm shared browser. Returns the
    violations and the final URL (post-redirect) so callers can detect a
    login-wall redirect."""
    settings = get_settings()
    browser, own_browser = await _acquire_browser()

    try:
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
            result = await page.evaluate("async () => await axe.run(document)")
            violations = result.get("violations", [])
            for violation in violations[:MAX_SCREENSHOTS]:
                selector = _node_selector(violation.get("nodes", []))
                violation["screenshot"] = await _capture_element_screenshot(page, selector)
            return violations, final_url
        finally:
            await context.close()
    finally:
        if own_browser:
            await browser.close()


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
            violations, final_url = await _run_axe(url, axe_path, storage_state)

        issues = normalize_violations(violations)
        notice = None
        if _looks_like_login_wall(url, final_url):
            notice = (
                "The page redirected to what looks like a login screen, so these "
                "results may reflect the login page rather than the intended page. "
                "Provide a valid session (storage state) to scan authenticated content."
            )
        return ScanResponse(url=url, issues=issues, summary=_summary(issues), source="live", notice=notice)
    except Exception as exc:
        log_error(f"Live scan failed for url={url}: {type(exc).__name__}: {exc}", exc=exc)
        return fallback_scan(url, f"Live scan failed; demo results shown. {type(exc).__name__}")
