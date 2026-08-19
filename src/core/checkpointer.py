import logging
from typing import Optional, Any
from langgraph.checkpoint.memory import MemorySaver

from config.settings import settings

logger = logging.getLogger("PulseGraph.Checkpointer")

_GLOBAL_CHECKPOINTER: Optional[Any] = None
_GLOBAL_DB_POOL: Optional[Any] = None


def get_default_checkpointer(force_backend: Optional[str] = None) -> Any:
    """
    Returns the configured LangGraph execution checkpointer.
    - PostgresSaver: Production-grade persistent checkpointing in PostgreSQL.
    - MemorySaver: In-memory checkpointing for localized testing if explicitly configured.
    
    Rule:
    Production environment requires PostgresSaver. If initializing PostgresSaver fails in production,
    the application fails fast rather than silently falling back to MemorySaver.
    """
    global _GLOBAL_CHECKPOINTER, _GLOBAL_DB_POOL

    backend = (force_backend or settings.checkpoint_backend).lower()
    is_production = settings.environment.lower() == "production"

    if is_production and backend != "postgres":
        logger.error("Production environment requires PostgresSaver checkpointer backend.")
        raise ValueError("Production environment must use PostgresSaver checkpointer.")

    if _GLOBAL_CHECKPOINTER is not None and force_backend is None:
        return _GLOBAL_CHECKPOINTER

    if backend == "postgres" or is_production:
        try:
            from psycopg_pool import ConnectionPool
            from langgraph.checkpoint.postgres import PostgresSaver

            logger.info(f"Initializing persistent PostgresSaver checkpointer on database host: {settings.postgres_host}")
            
            if _GLOBAL_DB_POOL is None:
                _GLOBAL_DB_POOL = ConnectionPool(
                    conninfo=settings.database_url,
                    max_size=10,
                    kwargs={"autocommit": True}
                )
            
            postgres_checkpointer = PostgresSaver(_GLOBAL_DB_POOL)
            postgres_checkpointer.setup()
            
            logger.info("PostgresSaver checkpointer initialized and tables verified successfully.")
            _GLOBAL_CHECKPOINTER = postgres_checkpointer
            return _GLOBAL_CHECKPOINTER

        except Exception as e:
            logger.exception(f"Failed to initialize PostgresSaver checkpointer: {e}")
            if is_production:
                raise RuntimeError(f"Critical failure: PostgresSaver checkpointer initialization failed in production: {e}") from e
            logger.warning("Falling back to MemorySaver for development due to PostgreSQL checkpointer initialization failure.")
            _GLOBAL_CHECKPOINTER = MemorySaver()
            return _GLOBAL_CHECKPOINTER

    logger.info("Initializing in-memory MemorySaver checkpointer.")
    _GLOBAL_CHECKPOINTER = MemorySaver()
    return _GLOBAL_CHECKPOINTER


def close_checkpointer_pool() -> None:
    """Closes active PostgreSQL connection pool upon shutdown."""
    global _GLOBAL_DB_POOL, _GLOBAL_CHECKPOINTER
    if _GLOBAL_DB_POOL is not None:
        try:
            logger.info("Closing checkpointer PostgreSQL connection pool...")
            _GLOBAL_DB_POOL.close()
        except Exception as e:
            logger.warning(f"Error closing checkpointer connection pool: {e}")
        finally:
            _GLOBAL_DB_POOL = None
            _GLOBAL_CHECKPOINTER = None
