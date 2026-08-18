import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_swagger_and_openapi_documentation_endpoints():
    """Verify OpenAPI schema generation, Swagger UI (/docs), and ReDoc UI (/redoc)."""
    # 1. OpenAPI JSON Schema
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert schema["info"]["title"] == "PulseGraph AI — Clinical Decision Support Backend API"
    assert "paths" in schema
    assert "/api/auth/login" in schema["paths"]
    assert "/api/doctors" in schema["paths"]
    assert "/api/patients" in schema["paths"]
    assert "/api/clinical/sessions" in schema["paths"]

    # 2. Swagger UI /docs
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger-ui" in docs_resp.text.lower()

    # 3. ReDoc UI /redoc
    redoc_resp = client.get("/redoc")
    assert redoc_resp.status_code == 200
    assert "redoc" in redoc_resp.text.lower()
