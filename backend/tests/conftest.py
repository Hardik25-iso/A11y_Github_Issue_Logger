import pytest

from backend.app.core.config import clear_settings_cache
from backend.app.core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_settings_cache():
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # Clear in-memory rate-limit counters between tests so the shared limiter's
    # global default does not leak request budget across the suite.
    limiter.reset()
    yield
    limiter.reset()
