import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    ollama_base_url: str
    ollama_model: str
    ai_timeout_seconds: float
    anthropic_api_key: str
    anthropic_model: str
    github_token: str
    github_repo_owner: str
    github_repo_name: str
    frontend_origins: tuple[str, ...]
    enable_live_scan: bool
    scan_timeout_ms: int
    block_heavy_scan_resources: bool

    @property
    def default_repo(self) -> str:
        if self.github_repo_owner and self.github_repo_name:
            return f"{self.github_repo_owner}/{self.github_repo_name}"
        return ""

    @classmethod
    def from_env(cls) -> "Settings":
        from backend.app.core.security import validate_ollama_base_url
        origins = os.getenv("FRONTEND_ORIGINS", os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"))
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        validate_ollama_base_url(ollama_base_url)
        return cls(
            ai_provider=os.getenv("AI_PROVIDER", "template").lower(),
            ollama_base_url=ollama_base_url,
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "30")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_repo_owner=os.getenv("GITHUB_REPO_OWNER", ""),
            github_repo_name=os.getenv("GITHUB_REPO_NAME", ""),
            frontend_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
            enable_live_scan=os.getenv("ENABLE_LIVE_SCAN", "false").lower() == "true",
            scan_timeout_ms=int(os.getenv("SCAN_TIMEOUT_MS", "30000")),
            block_heavy_scan_resources=os.getenv("BLOCK_HEAVY_SCAN_RESOURCES", "true").lower() == "true",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
