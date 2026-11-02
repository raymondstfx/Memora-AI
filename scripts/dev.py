"""Cross-platform recipes; run with the activated repository virtual environment."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=BACKEND, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["api", "migrate", "check", "export-api"])
    args = parser.parse_args()
    if args.command == "api":
        run("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1")
    elif args.command == "migrate":
        run("-m", "alembic", "upgrade", "head")
    elif args.command == "export-api":
        run(str(ROOT / "scripts" / "export_openapi.py"))
    else:
        run("-m", "ruff", "check", ".", "../scripts")
        run("-m", "ruff", "format", "--check", ".", "../scripts")
        run("-m", "mypy", "app")
        run("-m", "pytest", "-m", "not integration", "-q")


if __name__ == "__main__":
    main()
