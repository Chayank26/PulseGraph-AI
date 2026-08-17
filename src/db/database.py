import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from config.settings import settings

logger = logging.getLogger("PulseGraph.Database")

# Create SQLAlchemy Engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.debug
)

# Session factory for DB transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base ORM class
Base = declarative_base()


def init_db() -> None:
    """Creates all database tables using SQLAlchemy metadata."""
    logger.info(f"Initializing PostgreSQL database schema against target host: {settings.postgres_host}:{settings.postgres_port}...")
    from src.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("PostgreSQL database tables created/verified successfully.")


def get_db() -> Generator[Session, None, None]:
    """Dependency generator yielding an isolated database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
