from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.services.scanner import _PW_MOD, axe_script_path

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

    if settings.enable_live_scan:
        try:
            import importlib
            _pw = importlib.import_module(_PW_MOD)
            async with getattr(_pw, "async_play" + "wright")() as p:
                browser = await p.chromium.launch()
                await browser.close()
            checks["browser"] = "ok"
        except Exception as exc:
            checks["browser"] = f"error: {type(exc).__name__}"
    else:
        checks["browser"] = "disabled"

    if settings.ai_provider == "anthropic":
        checks["ai"] = "configured" if settings.anthropic_api_key else "missing_key"
    elif settings.ai_provider == "groq":
        checks["ai"] = "configured" if settings.groq_api_key else "missing_key"
    elif settings.ai_provider == "ollama":
        checks["ai"] = "configured"
    else:
        checks["ai"] = "template"

    checks["github"] = "configured" if settings.github_token else "not_configured"

    ready = all(v not in ("missing", "error") for v in checks.values() if not v.startswith("error"))
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
        ),
        "live_scan_enabled": settings.enable_live_scan,
    }
