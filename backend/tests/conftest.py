import pytest

from backend.app.core.config import clear_settings_cache


@pytest.fixture(autouse=True)
def reset_settings_cache():
    clear_settings_cache()
    yield
    clear_settings_cache()
