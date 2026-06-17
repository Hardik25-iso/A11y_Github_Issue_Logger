import asyncio
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import log_error, log_info
from backend.app.core.security import validate_resolved_public_url
from backend.app.models import ScanIssue, ScanResponse

# Max concurrent live Playwright scans — prevents resource exhaustion
_SCAN_SEMAPHORE = asyncio.Semaphore(3)

# Warm browser shared across requests — contexts are isolated per scan
_playwright_instance: Any = None
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


async def init_browser_pool() -> None:
    global _playwright_instance, _browser
    if not get_settings().enable_live_scan:
        return
    try:
        import importlib
        _pw = importlib.import_module("playwright.async_api")
        _playwright_instance = await _pw.async_playwright().start()
        _browser = await _playwright_instance.chromium.launch()
        log_info("Browser pool initialised")
    except Exception as exc:
        log_error(f"Browser pool init failed: {exc}", exc=exc)


async def close_browser_pool() -> None:
    global _playwright_instance, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright_instance:
        await _playwright_instance.stop()
        _playwright_instance = None
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


def normalize_violations(violations: list[dict]) -> list[ScanIssue]:
    issues = []
    for violation in violations:
        tags = violation.get("tags", [])
        criterion = _criterion(tags)
        nodes = violation.get("nodes", [])
        raw_target = nodes[0].get("target", []) if nodes else []
        # axe-core uses nested lists for elements inside iframes; flatten to strings
        flat_target = [
            part
            for item in raw_target
            for part in (item if isinstance(item, list) else [item])
        ]
        issues.append(
            ScanIssue(
                id=violation.get("id", "axe-violation"),
                title=violation.get("help", "Accessibility violation"),
                severity=SEVERITY_MAP.get(violation.get("impact"), "Low"),  # type: ignore[arg-type]
                wcag_criterion=criterion,
                wcag_url=_wcag_url(criterion, violation.get("helpUrl", "")),
                element=nodes[0].get("html", "")[:300] if nodes else "",
                selector=" ".join(str(p) for p in flat_target) if flat_target else "",
                impact=violation.get("description", ""),
                description=violation.get("help", ""),
                occurrences=max(1, len(nodes)),
                tags=tags,
            )
        )
    return issues


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


async def _run_axe(url: str, axe_path: Path) -> list[dict]:
    """Run axe-core against url, reusing the warm shared browser."""
    global _browser
    settings = get_settings()

    # Fall back to launching a fresh browser if the pool isn't initialised
    if _browser is None or not _browser.is_connected():
        import importlib
        _pw = importlib.import_module("playwright.async_api")
        pw = await _pw.async_playwright().start()
        browser = await pw.chromium.launch()
        own_browser = True
    else:
        browser = _browser
        own_browser = False

    try:
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.route("**/*", _guarded_route)
            await page.goto(url, wait_until="domcontentloaded", timeout=settings.scan_timeout_ms)
            validate_resolved_public_url(page.url)
            await page.add_script_tag(path=str(axe_path))
            result = await page.evaluate("async () => await axe.run(document)")
            return result.get("violations", [])
        finally:
            await context.close()
    finally:
        if own_browser:
            await browser.close()


async def scan_url(url: str) -> ScanResponse:
    settings = get_settings()
    if not settings.enable_live_scan:
        return fallback_scan(url)

    try:
        validate_resolved_public_url(url)
        axe_path = axe_script_path()
        if not axe_path.exists():
            return fallback_scan(url, "Local axe-core bundle is missing; demo results shown.")

        async with _SCAN_SEMAPHORE:
            violations = await _run_axe(url, axe_path)

        issues = normalize_violations(violations)
        return ScanResponse(url=url, issues=issues, summary=_summary(issues), source="live")
    except Exception as exc:
        log_error(f"Live scan failed for url={url}: {type(exc).__name__}: {exc}", exc=exc)
        return fallback_scan(url, f"Live scan failed; demo results shown. {type(exc).__name__}")
