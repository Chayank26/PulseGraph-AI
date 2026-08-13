import os
import sqlite3
import logging
import bcrypt
from typing import Optional, Dict, Any

logger = logging.getLogger("PulseGraph.AuthDatabase")

DEFAULT_DB_PATH = os.path.join("data", "users.db")


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Ensure database directory exists and return SQLite connection."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize doctors database schema and insert seed data if needed."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS doctors (
                    doctor_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'Attending Physician',
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        logger.info(f"Database initialized at {db_path}")
        seed_default_doctor(db_path)
    finally:
        conn.close()


def seed_default_doctor(db_path: str = DEFAULT_DB_PATH) -> None:
    """Seed default test doctor (DOC-88204 / Dr. Sarah Chen) if not present."""
    default_id = "DOC-88204"
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT doctor_id FROM doctors WHERE doctor_id = ?", (default_id,))
        if cursor.fetchone() is None:
            hashed = bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            with conn:
                conn.execute("""
                    INSERT INTO doctors (doctor_id, full_name, department, role, password_hash)
                    VALUES (?, ?, ?, ?, ?)
                """, (default_id, "Dr. Sarah Chen", "Emergency Medicine", "Attending Physician", hashed))
            logger.info(f"Seeded default doctor {default_id} (Dr. Sarah Chen)")
    finally:
        conn.close()


def register_doctor(
    doctor_id: str,
    full_name: str,
    department: str,
    password: str,
    role: str = "Attending Physician",
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    """Register a new physician with bcrypt password hashing."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        with conn:
            conn.execute("""
                INSERT INTO doctors (doctor_id, full_name, department, role, password_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (doctor_id, full_name, department, role, hashed_pw))
        logger.info(f"Registered doctor {doctor_id} ({full_name})")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Registration failed: Doctor ID {doctor_id} already exists.")
        return False
    except Exception as e:
        logger.error(f"Error registering doctor {doctor_id}: {e}")
        return False
    finally:
        conn.close()


def authenticate_doctor(
    doctor_id: str,
    password: str,
    db_path: str = DEFAULT_DB_PATH
) -> Optional[Dict[str, Any]]:
    """Authenticate physician credentials against stored bcrypt hash."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT doctor_id, full_name, department, role, password_hash FROM doctors WHERE doctor_id = ?",
            (doctor_id,)
        )
        row = cursor.fetchone()
        if row is None:
            logger.warning(f"Authentication failed: Doctor ID '{doctor_id}' not found.")
            return None

        stored_hash = row["password_hash"]
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            logger.info(f"Doctor {doctor_id} authenticated successfully.")
            return {
                "doctor_id": row["doctor_id"],
                "full_name": row["full_name"],
                "department": row["department"],
                "role": row["role"]
            }
        else:
            logger.warning(f"Authentication failed: Invalid password for doctor '{doctor_id}'.")
            return None
    except Exception as e:
        logger.error(f"Authentication error for {doctor_id}: {e}")
        return None
    finally:
        conn.close()
