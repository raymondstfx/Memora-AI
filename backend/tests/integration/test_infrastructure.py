"""Run only against an isolated test database; downgrade drops baseline metadata."""

import os

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from alembic import command
from app.core.config import get_settings
from app.db.session import build_engine
from app.main import create_app

pytestmark = pytest.mark.integration


def test_real_migration_cycle_and_health() -> None:
    if os.environ.get("MEMORA_TEST_DATABASE_RESET") != "1":
        pytest.skip("Requires isolated database and MEMORA_TEST_DATABASE_RESET=1")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = build_engine(get_settings())
    assert (engine.url.database or "").endswith(("_test", "_isolated")), (
        "Migration reversal is allowed only on an explicitly named test database"
    )
    try:
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT '[1,2,3]'::vector <-> '[1,2,3]'::vector")
                )
                == 0
            )
        with TestClient(create_app()) as client:
            assert client.get("/api/health").status_code == 200
        command.downgrade(config, "base")
        assert "system_metadata" not in inspect(engine).get_table_names()
        with TestClient(create_app()) as client:
            response = client.get("/api/health")
            assert response.status_code == 503
            assert response.json()["details"]["dependencies"]["schema"] == "unavailable"
        command.upgrade(config, "head")
        with TestClient(create_app()) as client:
            assert client.get("/api/health").status_code == 200
        command.check(config)
    finally:
        engine.dispose()
