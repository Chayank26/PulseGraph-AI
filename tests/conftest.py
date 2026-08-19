import pytest
from src.db.database import SessionLocal, init_db


@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional SQLAlchemy database session for tests."""
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
