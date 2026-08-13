import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import jwt

logger = logging.getLogger("PulseGraph.AuthSession")

DEFAULT_SECRET_KEY = os.getenv("PULSEGRAPH_JWT_SECRET", "pulsegraph_clinical_secret_key_2026")
ALGORITHM = "HS256"


def save_persistent_session(
    doctor_info: Dict[str, Any],
    secret_key: str = DEFAULT_SECRET_KEY,
    expires_days: int = 7
) -> str:
    """Generate a signed JWT token for persistent physician login session."""
    now = datetime.now(timezone.utc)
    payload = {
        "doctor_id": doctor_info["doctor_id"],
        "full_name": doctor_info["full_name"],
        "department": doctor_info["department"],
        "role": doctor_info.get("role", "Attending Physician"),
        "iat": now,
        "exp": now + timedelta(days=expires_days)
    }
    token = jwt.encode(payload, secret_key, algorithm=ALGORITHM)
    logger.info(f"Generated persistent JWT session token for doctor: {doctor_info['doctor_id']}")
    return token


def load_persistent_session(
    token: str,
    secret_key: str = DEFAULT_SECRET_KEY
) -> Optional[Dict[str, Any]]:
    """Decode and validate a persistent JWT session token."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return {
            "doctor_id": payload["doctor_id"],
            "full_name": payload["full_name"],
            "department": payload["department"],
            "role": payload.get("role", "Attending Physician")
        }
    except jwt.ExpiredSignatureError:
        logger.warning("Persistent session token has expired.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid session token: {e}")
        return None


def clear_persistent_session() -> None:
    """Helper placeholder for session cleanup."""
    logger.info("Cleared persistent session.")
