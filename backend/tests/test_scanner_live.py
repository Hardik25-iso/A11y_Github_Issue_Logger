"""
Integration tests that drive a real Chromium via Playwright and scan fixture
pages. Skipped unless ENABLE_LIVE_SCAN=true is set.

The fixtures are served from a fake public host (https://fixture.a11y.test)
by fulfilling requests from the client-side route handler, rather than from a
127.0.0.1 server: the SSRF guard rightly rejects loopback URLs, and a remote
browser could not reach the test machine's loopback anyway.

Run manually:
    ENABLE_LIVE_SCAN=true python -m pytest backend/tests/test_scanner_live.py -v
"""

import asyncio
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from backend.app.services import scanner
from backend.app.services.scanner import scan_url

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_HOST = "fixture.a11y.test"
FIXTURE_ORIGIN = f"https://{FIXTURE_HOST}"

pytestmark = pytest.mark.skipif(
    os.getenv("ENABLE_LIVE_SCAN", "false").lower() != "true",
    reason="ENABLE_LIVE_SCAN is not set to true",
)


@pytest.fixture(autouse=True)
def serve_fixtures(monkeypatch):
    """Answer requests to FIXTURE_HOST from the fixtures/ directory and abort
    everything else, so scans never touch the network."""
    real_validate = scanner.validate_resolved_public_url

    def validate(url: str) -> str:
        if urlsplit(url).hostname == FIXTURE_HOST:
            return url
        return real_validate(url)

    async def fixture_route(route):
        parsed = urlsplit(route.request.url)
        path = FIXTURE_DIR / parsed.path.lstrip("/")
        if parsed.hostname == FIXTURE_HOST and path.is_file():
            await route.fulfill(path=str(path))
        else:
            await route.abort()

    monkeypatch.setattr(scanner, "validate_resolved_public_url", validate)
    monkeypatch.setattr(scanner, "_guarded_route", fixture_route)


def _scan(page: str, storage_state: dict | None = None):
    result = asyncio.run(scan_url(f"{FIXTURE_ORIGIN}/{page}", storage_state))
    # A fallback must never satisfy a live test: the demo data happens to
    # contain the same rule ids the assertions look for.
    assert result.source == "live", result.notice
    return result


def test_detects_image_alt_violation():
    rule_ids = {issue.id for issue in _scan("violations.html").issues}
    assert "image-alt" in rule_ids, f"Expected image-alt, got: {rule_ids}"


def test_detects_button_name_violation():
    rule_ids = {issue.id for issue in _scan("violations.html").issues}
    assert "button-name" in rule_ids, f"Expected button-name, got: {rule_ids}"


def test_normalises_severity_correctly():
    severities = {issue.severity for issue in _scan("violations.html").issues}
    assert severities <= {"Critical", "High", "Medium", "Low"}


def test_summary_matches_issue_count():
    result = _scan("violations.html")
    assert sum(result.summary.values()) == len(result.issues)


def test_each_issue_has_wcag_criterion():
    for issue in _scan("violations.html").issues:
        assert issue.wcag_criterion, f"Issue {issue.id} has no WCAG criterion"
        parts = issue.wcag_criterion.split(".")
        assert len(parts) == 3, f"Criterion {issue.wcag_criterion!r} has wrong format"


def test_storage_state_reaches_the_scanned_page():
    signed_out = {issue.id for issue in _scan("session.html").issues}
    assert "button-name" not in signed_out

    storage_state = {
        "cookies": [
            {
                "name": "a11y_session",
                "value": "1",
                "domain": FIXTURE_HOST,
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            }
        ],
        "origins": [],
    }
    signed_in = {issue.id for issue in _scan("session.html", storage_state).issues}
    assert "button-name" in signed_in, f"Session cookie not applied, got: {signed_in}"
