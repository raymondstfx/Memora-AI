"""Isolated Phase 1 acceptance with a visibly synthetic, test-only HTTP upstream."""

import os
import subprocess
import sys
import time
from urllib.request import urlopen

import test_infrastructure as infrastructure

PROJECT = "memora-phase1-test"


def main() -> None:
    env = infrastructure.ENV
    env.update(
        {
            "MEMORA_CHAT_TEST": "1",
            "LLM_PROVIDER": "openai_compatible",
            "LLM_API_KEY": "test-only-credential",
            "LLM_MODEL": "test-model",
            "LLM_BASE_URL": "http://host.docker.internal:58901/v1",
            "LLM_TOTAL_TIMEOUT_SECONDS": "30",
            "LLM_MAX_RETRIES": "0",
        }
    )
    infrastructure.COMPOSE = [
        "docker",
        "compose",
        "-p",
        PROJECT,
        "--profile",
        "app",
    ]
    # No production setting selects this fixture. It runs as a separate test process.
    child_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "fake_provider:app",
            "--app-dir",
            str(infrastructure.ROOT / "backend/tests"),
            "--host",
            "0.0.0.0",
            "--port",
            "58901",
            "--no-access-log",
        ],
        cwd=infrastructure.ROOT,
        env=child_env,
    )
    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError("Test upstream failed to start")
            try:
                with urlopen("http://127.0.0.1:58901/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError("Test upstream startup timed out")
        infrastructure.main()
        print(
            "PASS: Phase 1 keyless implementation acceptance "
            "(test upstream, not real API)"
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
