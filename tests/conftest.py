import os
import pytest
from src.db.database import SessionLocal, init_db
from src.core import checkpointer

# Ensure test suite defaults to isolated checkpointer backend unless explicitly overridden
os.environ["CHECKPOINT_BACKEND"] = "memory"


@pytest.fixture(scope="function", autouse=True)
def reset_checkpointer():
    """Resets global checkpointer singleton between tests for clean state isolation."""
    checkpointer._GLOBAL_CHECKPOINTER = None


@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional SQLAlchemy database session for tests."""
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
