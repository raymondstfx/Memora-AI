"""Real Phase 2 Compose/RQ/PDF acceptance with explicitly injected test HTTP API."""

import sys

import test_infrastructure as infrastructure
import test_phase1


def main() -> None:
    sys.path.insert(0, str(infrastructure.ROOT / "backend"))
    from tests.pdf_fixtures import pdf_bytes

    folder = infrastructure.ROOT / "data" / "phase2-fixtures"
    folder.mkdir(parents=True, exist_ok=True)
    fixture = folder / "project_brief.pdf"
    fixture.write_bytes(pdf_bytes())
    infrastructure.ENV.update(
        {
            "MEMORA_PDF_TEST": "1",
            "TEST_PDF_PATH": str(fixture),
            "EMBEDDING_PROVIDER": "openai_compatible",
            "EMBEDDING_MODEL": "fixture-embedding",
            "EMBEDDING_DIMENSIONS": "16",
            "EMBEDDING_API_KEY": "test-only-credential",
            "EMBEDDING_BASE_URL": "http://host.docker.internal:58901/v1",
            "EMBEDDING_MAX_RETRIES": "0",
        }
    )
    test_phase1.PROJECT = "memora-phase2-test"
    test_phase1.main()
    print("PASS: Phase 2 PDF/RQ/hybrid/citation acceptance (test providers only)")


if __name__ == "__main__":
    main()
