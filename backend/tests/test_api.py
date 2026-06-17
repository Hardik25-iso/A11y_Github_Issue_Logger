import logging

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.logging import _safe
from backend.app.services.scanner import _SCAN_SEMAPHORE

client = TestClient(app)


def test_health():
    data = client.get("/health").json()
    assert data["status"] in ("ready", "degraded")
    assert "checks" in data


def test_scan_fallback_returns_structured_issues(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_SCAN", "false")
    response = client.post("/api/scan", json={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "fallback"
    assert data["issues"][0]["wcag_criterion"]
    assert sum(data["summary"].values()) == len(data["issues"])


def test_generate_template(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "template")
    scan = client.post("/api/scan", json={"url": "https://example.com"}).json()
    response = client.post(
        "/api/generate-issue",
        json={"url": scan["url"], "scan_issue": scan["issues"][0], "reference_issue": None},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "template"
    assert response.json()["generated_issue"]["acceptance_criteria"]


def test_search_uses_fallback_without_repo():
    scan = client.post("/api/scan", json={"url": "https://example.com"}).json()
    response = client.post(
        "/api/search-issues",
        json={"issue": scan["issues"][0], "repo": None},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert len(response.json()["similar_issues"]) >= 1


def test_scan_rejects_local_and_private_urls():
    for url in ("http://localhost:8000", "http://127.0.0.1", "http://192.168.1.2"):
        response = client.post("/api/scan", json={"url": url})
        assert response.status_code == 422


def test_search_rejects_invalid_repository_format():
    scan = client.post("/api/scan", json={"url": "https://example.com"}).json()
    response = client.post(
        "/api/search-issues",
        json={"issue": scan["issues"][0], "repo": "not-a-repository"},
    )
    assert response.status_code == 422


def test_config_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-key")
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert body["github_configured"] is True
    assert body["ai_configured"] is True
    assert "secret-token" not in response.text
    assert "secret-key" not in response.text


def test_cors_allows_configured_origin():
    # Default FRONTEND_ORIGINS in test env is http://localhost:5173
    response = client.options(
        "/api/scan",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin():
    response = client.options(
        "/api/scan",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_scan_semaphore_has_concurrency_cap():
    # Semaphore value reflects the configured cap (default 3)
    assert _SCAN_SEMAPHORE._value == 3


def test_log_redacts_secrets():
    assert _safe("Bearer sk-ant-api03-secret") == "Bearer [REDACTED]"
    assert _safe("token ghp_abc123") == "token [REDACTED]"
    assert _safe("normal log message") == "normal log message"


def test_health_returns_readiness_structure():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert data["status"] in ("ready", "degraded")
    assert "axe_bundle" in data["checks"]
    assert "ai" in data["checks"]
    assert "github" in data["checks"]


def test_livez_is_trivial():
    assert client.get("/livez").json() == {"status": "ok"}


def test_config_reports_ollama_without_exposing_internal_url(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://private-ai-host:11434")
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["ai_provider"] == "ollama"
    assert response.json()["ai_configured"] is True
    assert "private-ai-host" not in response.text
