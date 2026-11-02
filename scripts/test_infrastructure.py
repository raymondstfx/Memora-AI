"""Isolated real Compose acceptance test. Never resets the development database."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    **os.environ,
    "POSTGRES_USER": "memora",
    "POSTGRES_PASSWORD": "memora_test_only",
    "POSTGRES_DB": "memora_test",
    "POSTGRES_PORT": "55432",
    "REDIS_PORT": "56379",
    "API_PORT": "58000",
    "FRONTEND_PORT": "55173",
    "DATABASE_URL": "postgresql+psycopg://memora:memora_test_only@127.0.0.1:55432/memora_test",
    "REDIS_URL": "redis://127.0.0.1:56379/0",
    "MEMORA_TEST_DATABASE_RESET": "1",
    "TEST_BASE_URL": "http://127.0.0.1:55173",
}
COMPOSE = ["docker", "compose", "-p", "memora-phase0-test", "--profile", "app"]


def run(args: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, env=ENV, check=True)


def compose(*args: str) -> None:
    run([*COMPOSE, *args])


def health(port: int, expected: int = 200) -> dict[str, object]:
    try:
        response = urlopen(f"http://127.0.0.1:{port}/api/health", timeout=15)
    except HTTPError as error:
        response = error
    with response:
        assert response.status == expected, response.read().decode()
        return json.loads(response.read())  # type: ignore[no-any-return]


def main() -> None:
    try:
        compose("up", "--build", "-d", "--wait", "--wait-timeout", "180")
        run(
            [sys.executable, "-m", "pytest", "tests/integration", "-q"],
            ROOT / "backend",
        )
        health(58000)
        health(55173)  # Real Nginx -> API -> dependency path.
        compose(
            "exec", "-T", "redis", "redis-cli", "SET", "phase0:persistence", "verified"
        )
        compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "memora",
            "-d",
            "memora_test",
            "-c",
            "INSERT INTO system_metadata(key, value) "
            "VALUES ('restart_probe', 'verified') "
            "ON CONFLICT (key) DO UPDATE SET value = 'verified'",
        )
        compose("restart", "postgres", "redis")
        compose("up", "-d", "--wait", "postgres", "redis")
        health(58000)
        result = subprocess.check_output(
            [*COMPOSE, "exec", "-T", "redis", "redis-cli", "GET", "phase0:persistence"],
            cwd=ROOT,
            env=ENV,
            text=True,
        )
        assert result.strip() == "verified"
        result = subprocess.check_output(
            [
                *COMPOSE,
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "memora",
                "-d",
                "memora_test",
                "-tAc",
                "SELECT value FROM system_metadata WHERE key = 'restart_probe'",
            ],
            cwd=ROOT,
            env=ENV,
            text=True,
        )
        assert result.strip() == "verified"
        compose("stop", "redis")
        assert health(58000, 503)["code"] == "DEPENDENCIES_UNAVAILABLE"
        compose("up", "-d", "--wait", "redis")
        health(58000)
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        assert npm, "npm is required for browser checks"
        run([npm, "run", "test:e2e"], ROOT / "frontend")
        print(
            "PASS: full stack, migrations, pgvector, dependency failure/recovery, "
            "restart persistence, browser checks"
        )
    finally:
        compose("logs", "--no-color", "--tail", "25", "api", "migrate", "frontend")
        # Only the fixed isolated project and its disposable test volumes are removed.
        compose("down", "--volumes")


if __name__ == "__main__":
    main()
