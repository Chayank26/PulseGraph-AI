import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Authentication & Security
    pulsegraph_jwt_secret: str = "pulsegraph_clinical_jwt_secret_key_2026"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 10080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings singleton instance
settings = Settings()
