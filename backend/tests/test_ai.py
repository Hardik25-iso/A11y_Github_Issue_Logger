import asyncio

import pytest

from backend.app.core.config import Settings
from backend.app.models import GeneratedIssue, ScanIssue
from backend.app.services import generator
from backend.app.services.ai_client import AIProviderError, _extract_json, provider_order


def settings(provider: str, anthropic_key: str = "") -> Settings:
    return Settings(
        ai_provider=provider,
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen3:8b",
        ai_timeout_seconds=1,
        anthropic_api_key=anthropic_key,
        anthropic_model="claude-test",
        github_token="",
        github_repo_owner="",
        github_repo_name="",
        frontend_origins=("http://localhost:5173",),
        enable_live_scan=False,
        scan_timeout_ms=30000,
        block_heavy_scan_resources=True,
    )


def scan_issue() -> ScanIssue:
    return ScanIssue(
        id="button-name",
        title="Buttons must have discernible text",
        severity="High",
        wcag_criterion="4.1.2",
        wcag_url="https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html",
        element="<button></button>",
        selector="button.search",
        impact="Screen reader users cannot determine the button purpose.",
        description="The button has no accessible name.",
        occurrences=1,
        tags=["accessibility", "buttons"],
    )


def generated_data() -> dict:
    return GeneratedIssue(
        title="[A11y] Search button needs an accessible name",
        description="The search button has no accessible name and cannot be identified by screen reader users.",
        repro_steps=["Open the page.", "Focus the search button.", "Observe its accessible name."],
        expected_result="The button is announced as Search.",
        actual_result="The button is announced without a name.",
        severity="High",
        labels=["accessibility", "bug"],
        acceptance_criteria=["The button has an accessible name.", "The axe rule passes."],
        environment="Chrome and NVDA",
        wcag_reference="https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html",
    ).model_dump()


def test_provider_order():
    assert provider_order(settings("ollama")) == ["ollama"]
    assert provider_order(settings("anthropic", "key")) == ["anthropic"]
    assert provider_order(settings("auto", "key")) == ["ollama", "anthropic"]
    assert provider_order(settings("template")) == []


def test_extract_json_accepts_plain_json_and_markdown_fence():
    assert _extract_json('{"title": "Example"}') == {"title": "Example"}
    assert _extract_json('```json\n{"title": "Example"}\n```') == {"title": "Example"}
    with pytest.raises(AIProviderError):
        _extract_json("not-json")


def test_generation_uses_selected_ai_provider(monkeypatch):
    async def fake_generate_json(system: str, prompt: str):
        assert "accessibility engineer" in system
        assert "button-name" in prompt
        return generated_data(), "ollama"

    monkeypatch.setattr(generator, "generate_json", fake_generate_json)
    issue, source = asyncio.run(generator.generate_issue("https://example.com", scan_issue(), None))
    assert source == "ollama"
    assert issue.title.startswith("[A11y]")


def test_generation_falls_back_when_provider_fails(monkeypatch):
    async def failed_generate_json(system: str, prompt: str):
        raise AIProviderError("provider unavailable")

    monkeypatch.setattr(generator, "generate_json", failed_generate_json)
    issue, source = asyncio.run(generator.generate_issue("https://example.com", scan_issue(), None))
    assert source == "template"
    assert issue.severity == "High"
