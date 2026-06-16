from fastapi import APIRouter

from backend.app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/config")
async def config() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "default_repo": settings.default_repo,
        "github_configured": bool(settings.github_token),
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_provider in {"ollama", "auto"} or (
            settings.ai_provider == "anthropic" and bool(settings.anthropic_api_key)
        ),
        "live_scan_enabled": settings.enable_live_scan,
    }
