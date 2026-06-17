import json
from typing import Any, Literal

import httpx

from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import log_error, log_warning

AIProvider = Literal["ollama", "anthropic"]


class AIProviderError(RuntimeError):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        value = "\n".join(lines[1:-1]).strip()
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AIProviderError("AI provider returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise AIProviderError("AI provider returned a non-object JSON response")
    return data


async def _ollama_json(system: str, prompt: str, settings: Settings) -> dict[str, Any]:
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.1},
    }
    # Use a short connect timeout so a missing Ollama instance fails fast
    # rather than blocking for the full ai_timeout_seconds before fallback.
    timeout = httpx.Timeout(connect=3.0, read=settings.ai_timeout_seconds, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
        return _extract_json(response.json()["message"]["content"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        log_warning(f"Ollama request failed: {type(exc).__name__}: {exc}")
        raise AIProviderError("Ollama request failed") from exc


async def _anthropic_json(system: str, prompt: str, settings: Settings) -> dict[str, Any]:
    if not settings.anthropic_api_key:
        raise AIProviderError("Anthropic API key is not configured")
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=settings.ai_timeout_seconds)
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_json(response.content[0].text)
    except Exception as exc:
        log_error(f"Anthropic request failed: {type(exc).__name__}: {exc}", exc=exc)
        raise AIProviderError("Anthropic request failed") from exc


def provider_order(settings: Settings) -> list[AIProvider]:
    if settings.ai_provider == "auto":
        providers: list[AIProvider] = ["ollama"]
        if settings.anthropic_api_key:
            providers.append("anthropic")
        return providers
    if settings.ai_provider == "ollama":
        return ["ollama"]
    if settings.ai_provider == "anthropic":
        return ["anthropic"]
    return []


async def generate_json(system: str, prompt: str) -> tuple[dict[str, Any], AIProvider]:
    settings = get_settings()
    for provider in provider_order(settings):
        try:
            if provider == "ollama":
                return await _ollama_json(system, prompt, settings), provider
            return await _anthropic_json(system, prompt, settings), provider
        except AIProviderError:
            log_warning(f"AI provider '{provider}' failed, trying next")
            continue
    log_error("All configured AI providers exhausted without a valid response")
    raise AIProviderError("No configured AI provider returned a valid response")
