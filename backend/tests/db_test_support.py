"""File-backed, migrated SQLite per test; never use the developer's DB."""
import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.database import create_database_engine, get_session
from app.main import app
from app.llm.mock_provider import MockLLMProvider
from app.seed import seed_data


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        # Historical single-level regression suites explicitly exercise rollback.
        legacy = patch.dict(os.environ, {"LEETCOACH_ENABLE_LEGACY_STARTER": "true"})
        legacy.start()
        self.addCleanup(legacy.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.url = URL.create("sqlite", database=str(Path(temporary.name) / "test.db"))
        self.engine = create_database_engine(self.url)
        self.addCleanup(self.engine.dispose)
        self.migrate("upgrade", "head")
        with Session(self.engine) as session, session.begin():
            seed_data(session)

        def test_session():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = test_session
        self.addCleanup(app.dependency_overrides.pop, get_session)
        provider_patch = patch("app.main.get_llm_provider", return_value=MockLLMProvider())
        provider_patch.start()
        self.addCleanup(provider_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def migrate(self, direction, revision):
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            getattr(command, direction)(config, revision)
