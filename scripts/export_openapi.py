import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

app = importlib.import_module("app.main").app

(ROOT / "docs/api/openapi.json").write_text(
    json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8"
)
