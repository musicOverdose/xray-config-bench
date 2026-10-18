"""Pytest fixtures and configuration."""

import pytest
from app.database import Database


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing a fresh isolated database in tmp_path."""
    db_file = tmp_path / "test_xray.db"
    db = Database(str(db_file))
    return db
