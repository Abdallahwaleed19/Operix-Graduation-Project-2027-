"""
tests/test_health.py
Verify system health, diagnostics, and OpenAPI documentation endpoints.
"""
from fastapi.testclient import TestClient


def test_liveness_endpoint(client: TestClient):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "platform" in data
    assert data["status"] == "online"
    assert data["docs"] == "/docs"


def test_health_check_envelope(client: TestClient):
    response = client.get("/health")
    # 200 if connected, 503 if disconnected
    assert response.status_code in (200, 503)
    body = response.json()
    assert "status" in body
    assert "data" in body
    assert "meta" in body
    assert body["data"]["app_name"] == "Operix Industrial AI Safety Platform"
    assert "database" in body["data"]
    assert "status" in body["data"]["database"]
    assert "components" in body["data"]
    assert body["data"]["components"].get("workforce_analytics") in ("module_loaded", "not_configured")
    assert body["data"]["components"].get("llm_rag_assistant") in ("module_loaded", "not_configured")


def test_v1_health_check_alias(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "data" in body


def test_openapi_docs_accessible(client: TestClient):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text or "swagger-ui" in response.text

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    schema = openapi_response.json()
    assert "openapi" in schema
    assert schema["info"]["title"] == "Operix Industrial AI Safety Platform"
