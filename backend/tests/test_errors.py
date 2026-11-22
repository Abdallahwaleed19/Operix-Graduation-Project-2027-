"""
tests/test_errors.py
Verify global error handling and standard error envelopes.
"""
from fastapi.testclient import TestClient


def test_404_error_envelope(client: TestClient):
    response = client.get("/api/v1/non_existent_endpoint")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert "error_code" in body
    assert "message" in body
    assert "timestamp" in body
