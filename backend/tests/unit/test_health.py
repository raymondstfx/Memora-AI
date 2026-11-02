from unittest.mock import AsyncMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_contract_and_request_id() -> None:
    with (
        patch(
            "app.api.health.postgres_readiness",
            return_value={"postgres": "ready", "pgvector": "ready", "schema": "ready"},
        ),
        patch("app.api.health.redis_readiness", new=AsyncMock(return_value="ready")),
        TestClient(create_app(Settings(_env_file=None))) as client,
    ):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        UUID(response.headers["x-request-id"])
        assert set(response.json()["dependencies"].values()) == {"ready"}


def test_unavailable_is_503_and_not_fabricated_success() -> None:
    with (
        patch(
            "app.api.health.postgres_readiness",
            return_value={
                "postgres": "unavailable",
                "pgvector": "unavailable",
                "schema": "unavailable",
            },
        ),
        patch("app.api.health.redis_readiness", new=AsyncMock(return_value="ready")),
        TestClient(create_app(Settings(_env_file=None))) as client,
    ):
        response = client.get("/api/health")
        assert response.status_code == 503
        body = response.json()
        assert body["code"] == "DEPENDENCIES_UNAVAILABLE"
        assert body["details"]["dependencies"]["postgres"] == "unavailable"
        assert body["request_id"] == response.headers["x-request-id"]
        assert "memora_local_only" not in response.text


def test_route_miss_uses_error_envelope() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/not-implemented")
        assert response.status_code == 404
        assert response.json()["code"] == "HTTP_ERROR"
        assert response.json()["request_id"] == response.headers["x-request-id"]


def test_unhandled_error_is_sanitized() -> None:
    app = create_app(Settings(_env_file=None))

    @app.get("/explode")
    def explode() -> None:
        raise RuntimeError("private-token")

    with TestClient(app) as client:
        response = client.get("/explode")
        assert response.status_code == 500
        assert response.json()["code"] == "INTERNAL_ERROR"
        assert "private-token" not in response.text


def test_allowed_cors_origin() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
