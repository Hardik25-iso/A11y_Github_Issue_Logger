from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.services.browser import local_browser_ready, quota_cooldown_remaining, remote_mode
from backend.app.services.scanner import axe_script_path

router = APIRouter()


@router.get("/livez")
async def liveness() -> dict[str, str]:
    """Trivial liveness probe — process is up."""
    return {"status": "ok"}


@router.get("/health")
async def health() -> dict:
    """Readiness probe — checks key dependencies are available."""
    settings = get_settings()
    checks: dict[str, str] = {}

    checks["axe_bundle"] = "ok" if axe_script_path().exists() else "missing"

    # Never launches or connects: a remote probe would spend browser quota on
    # every health check, and the warm local browser shows real readiness.
    if not settings.enable_live_scan:
        checks["browser"] = "disabled"
    elif remote_mode():
        checks["browser"] = "error: quota cooldown" if quota_cooldown_remaining() else "remote"
    else:
        checks["browser"] = "ok" if local_browser_ready() else "error: local browser not running"

    if settings.ai_provider == "anthropic":
        checks["ai"] = "configured" if settings.anthropic_api_key else "missing_key"
    elif settings.ai_provider == "groq":
        checks["ai"] = "configured" if settings.groq_api_key else "missing_key"
    elif settings.ai_provider == "ollama":
        checks["ai"] = "configured"
    else:
        checks["ai"] = "template"

    checks["github"] = "configured" if settings.github_token else "not_configured"

    ready = all(v not in ("missing",) and not v.startswith("error") for v in checks.values())
    return {"status": "ready" if ready else "degraded", "checks": checks}


@router.get("/api/config")
async def config() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "default_repo": settings.default_repo,
        "github_configured": bool(settings.github_token),
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_provider in {"ollama", "auto"} or (
            settings.ai_provider == "anthropic" and bool(settings.anthropic_api_key)
        ) or (
            settings.ai_provider == "groq" and bool(settings.groq_api_key)
        ),
        "live_scan_enabled": settings.enable_live_scan,
    }
