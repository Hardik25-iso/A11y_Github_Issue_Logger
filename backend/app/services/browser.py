"""Where scans get their browser: a local Chromium or a remote one over CDP.

Local (BROWSER_WS_ENDPOINT unset): a warm Chromium launched at startup and
shared across requests; contexts are isolated per scan. Without the warm
browser (tests, scripts), each session launches and fully tears down its own.

Remote (BROWSER_WS_ENDPOINT set): one CDP connection per session, closed
afterwards. Hosted browsers bill connected time and drop idle sessions, so a
warm remote browser would spend quota without saving anything.

Remote failures surface as BrowserUnavailable(kind) so callers can return an
honest, specific fallback instead of a generic error.
"""

import asyncio
import importlib
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import _safe, log_error, log_info, log_warning

_PW_MOD = "playwright.async_api"

# Required to launch Chromium reliably as root in a Docker container:
# --no-sandbox lifts the setuid-sandbox restriction (the container has no
# non-root user set up for it), and --disable-dev-shm-usage avoids crashes
# from Docker's default 64MB /dev/shm being exhausted during real page
# rendering (a bare launch()+close() with no page never hits this, which is
# why a naive browser-launch health check can pass while real scans fail).
CHROMIUM_LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]

# After the provider reports an exhausted quota, stop connecting for a while
# so every scan does not burn a failed handshake. In-memory on purpose: losing
# it on restart costs one extra failed connect.
QUOTA_COOLDOWN_SECONDS = 600
CONNECT_RETRY_DELAY_SECONDS = 1.0

_QUOTA_RE = re.compile(r"\b(429|402)\b|too many|limit exceeded|quota|payment required", re.IGNORECASE)
_AUTH_RE = re.compile(r"\b(401|403)\b|unauthori[sz]ed|forbidden", re.IGNORECASE)

# Warm local browser, started by init_browser_pool().
_pw_instance: Any = None
_browser: Any = None
# Playwright driver for remote connections, tied to the event loop it was
# started on (a new loop, e.g. per asyncio.run in tests, needs a new driver).
_remote_pw: Any = None
_remote_pw_loop: asyncio.AbstractEventLoop | None = None
_quota_cooldown_until = 0.0


class BrowserUnavailable(Exception):
    """The remote browser could not be used. kind is one of: quota, auth,
    connect, disconnected, timeout."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def remote_mode() -> bool:
    return bool(get_settings().browser_ws_endpoint)


def quota_cooldown_remaining() -> float:
    return max(0.0, _quota_cooldown_until - time.monotonic())


async def init_browser_pool() -> None:
    global _pw_instance, _browser
    if not get_settings().enable_live_scan:
        return
    if remote_mode():
        log_info("Remote browser configured; connecting per scan")
        return
    try:
        _pw = importlib.import_module(_PW_MOD)
        _pw_instance = await _pw.async_playwright().start()
        _browser = await _pw_instance.chromium.launch(args=CHROMIUM_LAUNCH_ARGS)
        log_info("Browser pool initialised")
    except Exception as exc:
        log_error(f"Browser pool init failed: {exc}", exc=exc)


async def close_browser_pool() -> None:
    global _pw_instance, _browser, _remote_pw, _remote_pw_loop
    if _browser:
        await _browser.close()
        _browser = None
    if _pw_instance:
        await _pw_instance.stop()
        _pw_instance = None
        log_info("Browser pool closed")
    if _remote_pw:
        await _remote_pw.stop()
        _remote_pw = None
        _remote_pw_loop = None


def local_browser_ready() -> bool:
    return _browser is not None and _browser.is_connected()


@asynccontextmanager
async def browser_session() -> AsyncIterator[Any]:
    """Yield a connected browser for one scan or login."""
    if remote_mode():
        async with _remote_session() as browser:
            yield browser
        return
    if local_browser_ready():
        yield _browser
        return
    # No warm browser: launch one for this session only, and stop its driver
    # too, so nothing outlives the session.
    _pw = importlib.import_module(_PW_MOD)
    pw = await _pw.async_playwright().start()
    try:
        browser = await pw.chromium.launch(args=CHROMIUM_LAUNCH_ARGS)
        try:
            yield browser
        finally:
            await browser.close()
    finally:
        await pw.stop()


@asynccontextmanager
async def _remote_session() -> AsyncIterator[Any]:
    browser = await _connect_remote()
    try:
        yield browser
    except BrowserUnavailable:
        raise
    except Exception:
        if not browser.is_connected():
            log_warning("Remote browser disconnected during a session")
            raise BrowserUnavailable("disconnected") from None
        raise
    finally:
        try:
            await browser.close()
        except Exception:
            pass  # already gone; the provider reaps the session itself


async def _remote_driver() -> Any:
    global _remote_pw, _remote_pw_loop
    loop = asyncio.get_running_loop()
    if _remote_pw is None or _remote_pw_loop is not loop:
        _pw = importlib.import_module(_PW_MOD)
        _remote_pw = await _pw.async_playwright().start()
        _remote_pw_loop = loop
    return _remote_pw


def classify_connect_error(exc: BaseException) -> str:
    # Redact first: the error repeats the endpoint URL, and digits inside the
    # token must not be mistaken for a 429/403 status.
    text = _safe(str(exc))
    if _QUOTA_RE.search(text):
        return "quota"
    if _AUTH_RE.search(text):
        return "auth"
    return "connect"


async def _connect_remote() -> Any:
    global _quota_cooldown_until
    if quota_cooldown_remaining():
        raise BrowserUnavailable("quota")
    settings = get_settings()
    driver = await _remote_driver()
    for attempt in (1, 2):
        try:
            return await driver.chromium.connect_over_cdp(
                settings.browser_ws_endpoint, timeout=settings.browser_connect_timeout_ms
            )
        except Exception as exc:
            kind = classify_connect_error(exc)
            # Only the redacted text is logged, and the original exception is
            # not chained (from None), so the token cannot reach a traceback.
            log_warning(f"Remote browser connect failed ({kind}, attempt {attempt}): {_safe(str(exc))[:300]}")
            if kind == "quota":
                _quota_cooldown_until = time.monotonic() + QUOTA_COOLDOWN_SECONDS
                raise BrowserUnavailable("quota") from None
            if kind == "auth" or attempt == 2:
                raise BrowserUnavailable(kind) from None
            await asyncio.sleep(CONNECT_RETRY_DELAY_SECONDS)
    raise AssertionError("unreachable")
