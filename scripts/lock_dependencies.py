"""Lock the dedicated project venv after an intentional dependency update."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
lines = subprocess.check_output(
    [sys.executable, "-m", "pip", "freeze", "--exclude-editable"], text=True
).splitlines()
dev_only = {
    "pytest",
    "ruff",
    "mypy",
    "mypy_extensions",
    "librt",
    "pathspec",
    "iniconfig",
    "pluggy",
    "pygments",
}
(root / "backend/requirements-dev.lock").write_text(
    "\n".join(lines) + "\n", encoding="utf-8"
)
(root / "backend/requirements.lock").write_text(
    "\n".join(line for line in lines if line.split("==")[0].lower() not in dev_only)
    + "\n",
    encoding="utf-8",
)
