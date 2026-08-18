import logging
import uvicorn

from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PulseGraph.Main")


def main():
    """Production FastAPI entrypoint for PulseGraph AI backend server."""
    logger.info("Initializing PulseGraph AI Backend Web Application...")
    logger.info(f"Target Environment: {settings.environment} | Log Level: {settings.log_level}")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
