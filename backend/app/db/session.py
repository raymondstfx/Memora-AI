from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    timeout = settings.dependency_timeout_seconds
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_timeout=timeout,
        hide_parameters=True,
        connect_args={
            "connect_timeout": timeout,
            "options": f"-c statement_timeout={timeout * 1000}",
        },
    )


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
