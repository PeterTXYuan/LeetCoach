"""Use exactly the same URL and SQLite settings as the API and seed command."""
from alembic import context

from app.database import Base, create_database_engine, get_database_url
from app import models  # noqa: F401 -- register all tables with Base.metadata

config = context.config
target_metadata = Base.metadata


def configure_and_run(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=get_database_url(), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    # Tests supply an isolated connection instead of touching the local DB.
    configure_and_run(config.attributes["connection"])
else:
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            configure_and_run(connection)
    finally:
        engine.dispose()
