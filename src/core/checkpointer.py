import logging
from typing import Optional, Any
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("PulseGraph.Checkpointer")

# Global singleton in-memory checkpointer for development environment
_GLOBAL_DEV_CHECKPOINTER: Optional[MemorySaver] = None


def get_default_checkpointer() -> Any:
    """
    Returns the configured LangGraph execution checkpointer.
    - Development environment: Returns an in-memory MemorySaver instance.
    - Production environment: Allows seamless injection of persistent checkpointers
      (e.g., PostgresSaver / RedisSaver) without modifying graph architecture.
    
    Note: Application domain data (doctors, patients, sessions, requests, results)
    is permanently stored in PostgreSQL. LangGraph checkpointer is strictly for
    in-flight workflow state machine step resumption.
    """
    global _GLOBAL_DEV_CHECKPOINTER
    if _GLOBAL_DEV_CHECKPOINTER is None:
        logger.info("Initializing default development MemorySaver checkpointer.")
        _GLOBAL_DEV_CHECKPOINTER = MemorySaver()
    return _GLOBAL_DEV_CHECKPOINTER
