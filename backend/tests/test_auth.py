"""Tests for the authenticated-scanning login flow (/api/login).

Playwright is mocked with in-memory fakes, mirroring how the scanner tests
avoid real browsers. The live path is exercised by monkeypatching
_acquire_browser and the resolved-URL check (DNS is unavailable in CI).
"""

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import LoginSelectors
from backend.app.services import auth as auth_service
from backend.app.services.auth import login_and_capture_session

client = TestClient(app)

PASSWORD = "s3cret-test-password"


class FakeLocator:
    def __init__(self, present=True, visible=True):
        self.present = present
        self.visible = visible
        self.filled_with = None

    @property
    def first(self):
        return self

    async def count(self):
        return 1 if self.present else 0

    async def is_visible(self):
        return self.visible

    async def fill(self, value):
        self.filled_with = value

    async def click(self):
        pass

    async def press(self, key):
        pass


class _Navigation:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakePage:
    """Simulates a login page. After submit, the page 'navigates' to post_url
    and, if login_succeeds, the password field disappears."""

    def __init__(self, login_url, post_url, login_succeeds=True, has_password_field=True):
        self.url = login_url
        self.post_url = post_url
        self.login_succeeds = login_succeeds
        self.username_locator = FakeLocator()
        self.password_locator = FakeLocator(present=has_password_field)
        self.submit_locator = FakeLocator()
        self.submitted = False

    async def route(self, pattern, handler):
        pass

    async def goto(self, url, wait_until=None, timeout=None):
        self.url = url

    def locator(self, selector):
        if "password" in selector:
            if self.submitted and self.login_succeeds:
                return FakeLocator(present=False)
            return self.password_locator
        if "submit" in selector or selector == "form button":
            return self.submit_locator
        return self.username_locator

    def expect_navigation(self, wait_until=None, timeout=None):
        self.submitted = True
        self.url = self.post_url
        return _Navigation()

    async def wait_for_load_state(self, state, timeout=None):
        pass

    async def screenshot(self, full_page=False, timeout=None):
        return b"fake-png-bytes"


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    async def new_page(self):
        return self.page

    async def storage_state(self):
        return {"cookies": [{"name": "session", "value": "abc"}], "origins": []}

    async def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, page):
        self.context = FakeContext(page)

    async def new_context(self, **kwargs):
        return self.context

    async def close(self):
        pass


def _login(page, monkeypatch, selectors=None):
    monkeypatch.setenv("ENABLE_LIVE_SCAN", "true")
    browser = FakeBrowser(page)

    async def fake_acquire():
        return browser, False

    monkeypatch.setattr(auth_service, "_acquire_browser", fake_acquire)
    monkeypatch.setattr(auth_service, "validate_resolved_public_url", lambda url: url)
    result = asyncio.run(
        login_and_capture_session("https://app.example.com/login", "tester@example.com", PASSWORD, selectors)
    )
    return result, browser


def test_login_success_returns_storage_state_and_screenshot(monkeypatch):
    page = FakePage("https://app.example.com/login", "https://app.example.com/dashboard")
    result, browser = _login(page, monkeypatch)
    assert result.success is True
    assert result.source == "live"
    assert result.storage_state == {"cookies": [{"name": "session", "value": "abc"}], "origins": []}
    assert result.screenshot.startswith("data:image/png;base64,")
    assert result.final_url == "https://app.example.com/dashboard"
    assert browser.context.closed  # nothing outlives the request but storage_state


def test_login_failure_when_login_wall_remains(monkeypatch):
    page = FakePage(
        "https://app.example.com/login", "https://app.example.com/login?error=1", login_succeeds=False
    )
    result, _ = _login(page, monkeypatch)
    assert result.success is False
    assert result.storage_state is None
    assert result.screenshot is None
    assert "still shows a login form" in result.notice


def test_login_failure_when_no_password_field_found(monkeypatch):
    page = FakePage(
        "https://app.example.com/login", "https://app.example.com/login", has_password_field=False
    )
    result, _ = _login(page, monkeypatch)
    assert result.success is False
    assert "password field" in result.notice


def test_login_uses_custom_selector_overrides(monkeypatch):
    page = FakePage("https://app.example.com/login", "https://app.example.com/home")
    selectors = LoginSelectors(username="#user-box", password="input[type=password]", submit="#go")
    result, _ = _login(page, monkeypatch, selectors)
    assert result.success is True
    assert page.username_locator.filled_with == "tester@example.com"


def test_login_disabled_returns_labeled_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_SCAN", "false")
    result = asyncio.run(
        login_and_capture_session("https://app.example.com/login", "user", PASSWORD)
    )
    assert result.success is False
    assert result.source == "fallback"
    assert "ENABLE_LIVE_SCAN" in result.notice


def test_login_unreachable_host_fails_structurally_without_leaking(monkeypatch, caplog):
    # .invalid never resolves, so the resolved-public-URL guard raises.
    monkeypatch.setenv("ENABLE_LIVE_SCAN", "true")
    with caplog.at_level(logging.INFO):
        result = asyncio.run(
            login_and_capture_session("https://no-such-host.invalid/login", "user", PASSWORD)
        )
    assert result.success is False
    assert result.source == "live"
    assert PASSWORD not in (result.notice or "")
    assert PASSWORD not in caplog.text


def test_credentials_never_appear_in_logs_or_response(monkeypatch, caplog):
    page = FakePage("https://app.example.com/login", "https://app.example.com/dashboard")
    with caplog.at_level(logging.INFO):
        result, _ = _login(page, monkeypatch)
    assert PASSWORD not in caplog.text
    assert "tester@example.com" not in caplog.text
    assert PASSWORD not in result.model_dump_json()


def test_api_login_rejects_local_urls():
    for url in ("http://localhost:8000/login", "http://127.0.0.1/login", "http://192.168.1.2/login"):
        response = client.post(
            "/api/login", json={"login_url": url, "username": "u", "password": "p"}
        )
        assert response.status_code == 422


def test_api_login_requires_credentials():
    response = client.post("/api/login", json={"login_url": "https://example.com/login"})
    assert response.status_code == 422


def test_api_login_fallback_response_shape(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_SCAN", "false")
    response = client.post(
        "/api/login",
        json={"login_url": "https://example.com/login", "username": "u", "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["source"] == "fallback"
    assert PASSWORD not in response.text


@pytest.mark.parametrize("field", ["username", "password", "submit"])
def test_login_selectors_reject_oversized_selectors(field):
    response = client.post(
        "/api/login",
        json={
            "login_url": "https://example.com/login",
            "username": "u",
            "password": "p",
            "selectors": {field: "x" * 300},
        },
    )
    assert response.status_code == 422
