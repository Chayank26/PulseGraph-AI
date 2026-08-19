import os
import logging
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("PulseGraph.Settings")


class Settings(BaseSettings):
    """Global configuration settings for PulseGraph AI framework."""
    
    # Environment
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_model: str = "gpt-4o"
    
    # Guardrails & Safety
    enable_safety_guardrails: bool = True
    max_diagnostic_candidates: int = 5
    
    # External APIs
    rxnorm_api_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    pubmed_api_key: Optional[str] = None

    # Database Configuration (Docker PostgreSQL)
    postgres_db: str = "pulsegraph"
    postgres_user: str = "pulsegraph_user"
    postgres_password: str = "pulsegraph_secret_2026"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = "postgresql://pulsegraph_user:pulsegraph_secret_2026@localhost:5432/pulsegraph"

    # LangGraph Execution Checkpointer Configuration
    checkpoint_backend: str = "postgres"  # Options: 'postgres', 'memory'

    # Authentication & Security
    pulsegraph_jwt_secret: str = "pulsegraph_clinical_jwt_secret_key_2026"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 10080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Ensures default development secrets are not used in production environment."""
        if self.environment.lower() == "production":
            if "pulsegraph_secret_2026" in self.database_url or "pulsegraph_secret_2026" in self.postgres_password:
                raise ValueError("Production environment must not use default database password.")
            if "pulsegraph_clinical_jwt_secret" in self.pulsegraph_jwt_secret:
                raise ValueError("Production environment must configure a secure PULSEGRAPH_JWT_SECRET.")
            if self.checkpoint_backend.lower() != "postgres":
                raise ValueError("Production environment must use 'postgres' checkpointer backend.")
        return self


# Global settings singleton instance
settings = Settings()
