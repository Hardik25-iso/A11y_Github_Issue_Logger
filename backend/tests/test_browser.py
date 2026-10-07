"""Tests for browser sessions: local launch, remote CDP connect, and how
remote failures (connect errors, quota, auth, disconnects, slow scans) turn
into honest fallbacks. Playwright is replaced by an in-memory fake module."""

import asyncio
import logging
import sys
import types

import pytest

from backend.app.core.logging import log_error
from backend.app.services import browser as browser_mod
from backend.app.services import scanner
from backend.app.services.browser import BrowserUnavailable, browser_session, classify_connect_error

ENDPOINT = "wss://production-sfo.browserless.io?token=sekret-4291-token"
SECRET = "sekret-4291-token"


class FakeBrowser:
    def __init__(self, version="137.0"):
        self.version = version
        self.connected = True
        self.closed = False

    def is_connected(self):
        return self.connected

    async def close(self):
        self.closed = True
        self.connected = False


class FakeChromium:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)  # FakeBrowser or Exception, consumed per call
        self.connect_calls = []
        self.launched = []

    async def connect_over_cdp(self, endpoint, timeout=None):
        self.connect_calls.append((endpoint, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def launch(self, args=None):
        launched = FakeBrowser("local")
        self.launched.append(launched)
        return launched


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium
        self.stopped = False

    async def stop(self):
        self.stopped = True


@pytest.fixture
def fake_pw(monkeypatch):
    """Install a fake playwright module; returns a function to set outcomes."""
    state = {"chromium": FakeChromium([]), "drivers": []}

    class _Starter:
        async def start(self):
            driver = FakePlaywright(state["chromium"])
            state["drivers"].append(driver)
            return driver

    module = types.ModuleType("fake_playwright")
    module.async_playwright = lambda: _Starter()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fake_playwright", module)
    monkeypatch.setattr(browser_mod, "_PW_MOD", "fake_playwright")
    monkeypatch.setattr(browser_mod, "CONNECT_RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(browser_mod, "_browser", None)
    monkeypatch.setattr(browser_mod, "_remote_pw", None)
    monkeypatch.setattr(browser_mod, "_remote_pw_loop", None)
    monkeypatch.setattr(browser_mod, "_quota_cooldown_until", 0.0)

    def configure(outcomes):
        state["chromium"].outcomes = list(outcomes)
        return state

    return configure


@pytest.fixture
def remote(monkeypatch):
    monkeypatch.setenv("BROWSER_WS_ENDPOINT", ENDPOINT)
    monkeypatch.setenv("BROWSER_CONNECT_TIMEOUT_MS", "1234")


async def _use_session():
    async with browser_session() as browser:
        return browser


# --- local mode --------------------------------------------------------------


def test_local_session_without_warm_browser_launches_and_tears_down(monkeypatch, fake_pw):
    monkeypatch.delenv("BROWSER_WS_ENDPOINT", raising=False)
    state = fake_pw([])
    used = asyncio.run(_use_session())
    assert used.version == "local"
    assert used.closed
    assert state["drivers"][0].stopped  # the driver no longer leaks
    assert state["chromium"].connect_calls == []


def test_local_session_reuses_warm_browser(monkeypatch, fake_pw):
    monkeypatch.delenv("BROWSER_WS_ENDPOINT", raising=False)
    warm = FakeBrowser("warm")
    monkeypatch.setattr(browser_mod, "_browser", warm)
    assert asyncio.run(_use_session()) is warm
    assert not warm.closed


# --- remote mode -------------------------------------------------------------


def test_remote_session_connects_with_endpoint_and_closes(remote, fake_pw):
    remote_browser = FakeBrowser()
    state = fake_pw([remote_browser])
    assert asyncio.run(_use_session()) is remote_browser
    assert state["chromium"].connect_calls == [(ENDPOINT, 1234)]
    assert remote_browser.closed
    assert state["chromium"].launched == []


def test_remote_connect_error_retries_once_then_gives_up(remote, fake_pw):
    state = fake_pw([ConnectionError("ECONNREFUSED"), ConnectionError("ECONNREFUSED")])
    with pytest.raises(BrowserUnavailable) as info:
        asyncio.run(_use_session())
    assert info.value.kind == "connect"
    assert len(state["chromium"].connect_calls) == 2


def test_remote_connect_recovers_on_retry(remote, fake_pw):
    remote_browser = FakeBrowser()
    state = fake_pw([TimeoutError("connect timed out"), remote_browser])
    assert asyncio.run(_use_session()) is remote_browser
    assert len(state["chromium"].connect_calls) == 2


def test_remote_quota_does_not_retry_and_starts_cooldown(remote, fake_pw):
    state = fake_pw([Exception(f"WebSocket error: {ENDPOINT} 429 Too Many Requests"), FakeBrowser()])
    for _ in range(2):
        with pytest.raises(BrowserUnavailable) as info:
            asyncio.run(_use_session())
        assert info.value.kind == "quota"
    # The second session short-circuited on the cooldown without connecting.
    assert len(state["chromium"].connect_calls) == 1
    assert browser_mod.quota_cooldown_remaining() > 0


def test_remote_auth_error_does_not_retry(remote, fake_pw):
    state = fake_pw([Exception("401 Unauthorized"), FakeBrowser()])
    with pytest.raises(BrowserUnavailable) as info:
        asyncio.run(_use_session())
    assert info.value.kind == "auth"
    assert len(state["chromium"].connect_calls) == 1


def test_digits_inside_the_token_are_not_read_as_status_codes():
    # The token contains "4291"; only the redacted text is classified.
    assert classify_connect_error(Exception(f"connect {ENDPOINT} ECONNRESET")) == "connect"
    assert classify_connect_error(Exception("wss://h?token=abc-429-x refused")) == "connect"


def test_remote_disconnect_mid_session_is_reported_and_browser_closed(remote, fake_pw):
    remote_browser = FakeBrowser()
    fake_pw([remote_browser])

    async def scan():
        async with browser_session() as browser:
            browser.connected = False
            raise RuntimeError("Target page, context or browser has been closed")

    with pytest.raises(BrowserUnavailable) as info:
        asyncio.run(scan())
    assert info.value.kind == "disconnected"


def test_page_error_with_live_connection_is_not_masked(remote, fake_pw):
    remote_browser = FakeBrowser()
    fake_pw([remote_browser])

    async def scan():
        async with browser_session():
            raise ValueError("page-level failure")

    with pytest.raises(ValueError):
        asyncio.run(scan())
    assert remote_browser.closed


def test_token_never_reaches_logs(remote, fake_pw, caplog):
    fake_pw([ConnectionError(f"connect {ENDPOINT} failed")] * 2)
    with caplog.at_level(logging.INFO):
        with pytest.raises(BrowserUnavailable):
            asyncio.run(_use_session())
        # A traceback logged elsewhere repeats the exception text; it must be
        # redacted too, not just the log message.
        try:
            raise ConnectionError(f"connect {ENDPOINT} failed")
        except ConnectionError as exc:
            log_error("unexpected", exc=exc)
    assert caplog.text
    assert SECRET not in caplog.text


# --- scanner integration -----------------------------------------------------


def _live_scan(monkeypatch, fake_run_axe):
    monkeypatch.setenv("ENABLE_LIVE_SCAN", "true")
    monkeypatch.setattr(scanner, "validate_resolved_public_url", lambda url: url)
    monkeypatch.setattr(scanner, "_run_axe", fake_run_axe)
    return asyncio.run(scanner.scan_url("https://example.com/"))


def test_scan_quota_returns_labeled_fallback(remote, monkeypatch):
    async def exhausted(*args):
        raise BrowserUnavailable("quota")

    result = _live_scan(monkeypatch, exhausted)
    assert result.source == "fallback"
    assert "quota is used up" in result.notice


def test_scan_retries_once_after_disconnect(remote, monkeypatch):
    calls = []

    async def flaky(*args):
        calls.append(1)
        if len(calls) == 1:
            raise BrowserUnavailable("disconnected")
        return [{"id": "image-alt", "impact": "critical", "tags": ["wcag111"], "nodes": []}], "https://example.com/"

    result = _live_scan(monkeypatch, flaky)
    assert result.source == "live"
    assert len(calls) == 2


def test_scan_does_not_retry_without_enough_budget(remote, monkeypatch):
    monkeypatch.setattr(scanner, "RETRY_MIN_SECONDS", 999)
    calls = []

    async def dropped(*args):
        calls.append(1)
        raise BrowserUnavailable("disconnected")

    result = _live_scan(monkeypatch, dropped)
    assert result.source == "fallback"
    assert "disconnected" in result.notice
    assert len(calls) == 1


def test_scan_over_total_budget_times_out(remote, monkeypatch):
    monkeypatch.setenv("SCAN_TOTAL_TIMEOUT_S", "0.05")

    async def slow(*args):
        await asyncio.sleep(5)

    result = _live_scan(monkeypatch, slow)
    assert result.source == "fallback"
    assert "took too long" in result.notice


def test_local_scan_has_no_total_budget(monkeypatch):
    # Local behaviour is unchanged: the remote-only cap must not apply.
    monkeypatch.delenv("BROWSER_WS_ENDPOINT", raising=False)
    monkeypatch.setenv("SCAN_TOTAL_TIMEOUT_S", "0.01")

    async def slower_than_cap(*args):
        await asyncio.sleep(0.1)
        return [], "https://example.com/"

    assert _live_scan(monkeypatch, slower_than_cap).source == "live"
