"""
Integration tests that launch a real Chromium browser via Playwright and scan
a local fixture page. Skipped unless ENABLE_LIVE_SCAN=true is set.

Run manually:
    ENABLE_LIVE_SCAN=true python -m pytest backend/tests/test_scanner_live.py -v
"""

import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest

from backend.app.services.scanner import scan_url

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def fixture_server():
    """Serve the fixtures/ directory on a random localhost port for the duration of the module."""
    handler = SimpleHTTPRequestHandler
    handler.directory = str(FIXTURE_DIR)  # type: ignore[attr-defined]
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def live_scan_enabled():
    return os.getenv("ENABLE_LIVE_SCAN", "false").lower() == "true"


@pytest.mark.skipif(not live_scan_enabled(), reason="ENABLE_LIVE_SCAN is not set to true")
class TestLiveScanner:
    def test_detects_image_alt_violation(self, fixture_server):
        import asyncio
        result = asyncio.run(scan_url(f"{fixture_server}/violations.html"))
        assert result.source == "live"
        rule_ids = {issue.id for issue in result.issues}
        assert "image-alt" in rule_ids, f"Expected image-alt, got: {rule_ids}"

    def test_detects_button_name_violation(self, fixture_server):
        import asyncio
        result = asyncio.run(scan_url(f"{fixture_server}/violations.html"))
        rule_ids = {issue.id for issue in result.issues}
        assert "button-name" in rule_ids, f"Expected button-name, got: {rule_ids}"

    def test_normalises_severity_correctly(self, fixture_server):
        import asyncio
        result = asyncio.run(scan_url(f"{fixture_server}/violations.html"))
        severities = {issue.severity for issue in result.issues}
        assert severities <= {"Critical", "High", "Medium", "Low"}

    def test_summary_matches_issue_count(self, fixture_server):
        import asyncio
        result = asyncio.run(scan_url(f"{fixture_server}/violations.html"))
        assert sum(result.summary.values()) == len(result.issues)

    def test_each_issue_has_wcag_criterion(self, fixture_server):
        import asyncio
        result = asyncio.run(scan_url(f"{fixture_server}/violations.html"))
        for issue in result.issues:
            assert issue.wcag_criterion, f"Issue {issue.id} has no WCAG criterion"
            parts = issue.wcag_criterion.split(".")
            assert len(parts) == 3, f"Criterion {issue.wcag_criterion!r} has wrong format"
