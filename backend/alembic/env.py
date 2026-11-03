from alembic import context
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import build_engine

target_metadata = Base.metadata


def include_name(name, type_, parent_names):  # type: ignore[no-untyped-def]
    # Owned by frozen Alembic DDL; official saver tables aren't ORM domain models.
    return not (
        type_ == "table"
        and name
        in {
            "checkpoint_migrations",
            "checkpoints",
            "checkpoint_blobs",
            "checkpoint_writes",
        }
    )


if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(get_settings())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
