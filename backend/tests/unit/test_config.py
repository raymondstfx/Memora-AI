import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_secrets_are_redacted() -> None:
    settings = Settings(_env_file=None)
    assert "memora_local_only" not in repr(settings)


@pytest.mark.parametrize("timeout", [0, 11])
def test_timeout_is_bounded(timeout: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, dependency_timeout_seconds=timeout)


@pytest.mark.parametrize("url", ["sqlite:///test.db", "not-a-url"])
def test_only_postgres_driver_is_accepted(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=SecretStr(url))
