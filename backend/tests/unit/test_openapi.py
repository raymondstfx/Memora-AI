import json
from pathlib import Path

from app.main import create_app


def test_checked_in_openapi_matches_running_application() -> None:
    snapshot = Path(__file__).resolve().parents[3] / "docs/api/openapi.json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == create_app().openapi()
