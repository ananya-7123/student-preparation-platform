"""
Authentication & Password Hashing utilities (PBKDF2-HMAC-SHA256 + Signed Bearer Tokens).
Uses only Python stdlib + SQLAlchemy so zero extra packages are required.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Student

load_dotenv()

TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
PBKDF2_ITERATIONS = 120_000


def _get_signing_secret() -> bytes:
    configured = (os.getenv("AUTH_SECRET_KEY") or "").strip()
    if configured:
        return configured.encode("utf-8")
    seed = (os.getenv("DB_PASSWORD") or "kiit-prep-local-dev").strip()
    return hashlib.sha256(f"{seed}:kiit-student-prep-auth".encode("utf-8")).digest()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, salt, hex_digest = stored_hash.split("$", 2)
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
        ).hex()
        return hmac.compare_digest(candidate, hex_digest)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(student_id: int, roll_number: str) -> str:
    payload = {
        "sub": student_id,
        "roll": roll_number,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(_get_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload_b64, sig_b64 = token.strip().split(".", 1)
        expected_sig = hmac.new(
            _get_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        provided_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def get_current_student_optional(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[Student]:
    if not authorization or not authorization.strip():
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    payload = decode_access_token(parts[1])
    if not payload or "sub" not in payload:
        return None
    return db.query(Student).filter(Student.id == int(payload["sub"])).first()


def get_current_student(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Student:
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
        )
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format.",
        )
    payload = decode_access_token(parts[1])
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again.",
        )
    student = db.query(Student).filter(Student.id == int(payload["sub"])).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student account no longer exists.",
        )
    return student


def ensure_auth_schema() -> None:
    """
    Idempotently create the students table and mock_attempts.student_id column
    in PostgreSQL at startup if they do not yet exist.
    """
    try:
        Base.metadata.create_all(bind=engine, tables=[Student.__table__])
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE mock_attempts
                    ADD COLUMN IF NOT EXISTS student_id INTEGER REFERENCES students(id) ON DELETE SET NULL
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_students_roll_lower ON students (LOWER(roll_number))"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mock_attempts_student_id ON mock_attempts (student_id)"
                )
            )
    except Exception:
        # Avoid blocking startup if inspected offline without live DB
        pass

