"""Isolated real Compose acceptance test. Never resets the development database."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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
        pdf_id = None
        if ENV.get("MEMORA_PDF_TEST") == "1":
            import httpx

            with httpx.Client(
                trust_env=False, base_url="http://127.0.0.1:58000", timeout=30
            ) as client:
                with Path(ENV["TEST_PDF_PATH"]).open("rb") as original:
                    uploaded = client.post(
                        "/api/documents/upload",
                        files={
                            "file": ("project_brief.pdf", original, "application/pdf")
                        },
                    )
                assert uploaded.status_code == 202, (
                    f"HTTP {uploaded.status_code}: {uploaded.text}"
                )
                pdf_id = uploaded.json()["document_id"]
                for _ in range(120):
                    state = client.get(f"/api/jobs/{uploaded.json()['job_id']}").json()
                    if state["status"] in ("succeeded", "failed"):
                        break
                    time.sleep(0.5)
                assert state["status"] == "succeeded", state
        chat_id = None
        if ENV.get("MEMORA_CHAT_TEST") == "1":
            body = json.dumps({"message": "restart persistence probe"}).encode()
            with urlopen(
                Request(
                    "http://127.0.0.1:58000/api/chat/stream",
                    data=body,
                    headers={"Content-Type": "application/json"},
                ),
                timeout=30,
            ) as result:
                frames = [
                    json.loads(line[6:])
                    for line in result.read().decode().splitlines()
                    if line.startswith("data: ")
                ]
            assert frames[-1]["event"] == "message_end"
            chat_id = frames[0]["conversation_id"]
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
        compose(
            "restart",
            "postgres",
            "redis",
            *(["api"] if chat_id else []),
            *(["worker"] if pdf_id else []),
        )
        compose("up", "-d", "--wait", "postgres", "redis")
        if chat_id:
            compose("up", "-d", "--wait", "api", *(["worker"] if pdf_id else []))
        health(58000)
        if pdf_id:
            with httpx.Client(
                trust_env=False, base_url="http://127.0.0.1:58000", timeout=30
            ) as client:
                assert (
                    client.get(f"/api/documents/{pdf_id}").json()["status"] == "ready"
                )
                assert (
                    client.get(f"/api/documents/{pdf_id}/file").content
                    == Path(ENV["TEST_PDF_PATH"]).read_bytes()
                )
                sources = client.post(
                    "/api/documents/search",
                    json={"question": "API deadline", "document_ids": [pdf_id]},
                ).json()["sources"]
                assert sources and sources[0]["page_no"] == 1
        if chat_id:
            compose("up", "-d", "--wait", "api")
            with urlopen(
                f"http://127.0.0.1:58000/api/conversations/{chat_id}/messages",
                timeout=10,
            ) as result:
                rows = json.loads(result.read())
            assert rows[-1]["status"] == "complete"
            assert "restart persistence probe" in rows[-1]["content"]
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
