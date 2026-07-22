
import base64
import hashlib
import hmac
import os
import re
import secrets
import time

from fastapi import HTTPException, Request
from sqlalchemy import select

from database import SessionLocal
from models import PasswordReset, User

USERNAME = os.environ.get("APP_USERNAME", "")
PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-insecure-change-in-production")
USERNAME_PATTERN = re.compile(r"^[a-z0-9_-]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_ITERATIONS = 600_000
RESET_CODE_TTL_SECONDS = 10 * 60
RESET_CODE_MAX_ATTEMPTS = 5


def normalize_username(username: str) -> str:
    return username.strip().lower()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_new_account(username: str, password: str, email: str) -> tuple[str, str]:
    normalized = normalize_username(username)
    normalized_email = normalize_email(email)
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Username must be 3–32 characters using letters, numbers, _ or -")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 8 characters")
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise ValueError("Please enter a valid email address")
    if USERNAME and normalized == normalize_username(USERNAME):
        raise ValueError("That username is already in use")
    with SessionLocal() as session:
        if session.get(User, normalized) is not None:
            raise ValueError("That username is already in use")
    return normalized, normalized_email


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_account(username: str, password: str, email: str) -> str:
    normalized, normalized_email = validate_new_account(username, password, email)
    with SessionLocal.begin() as session:
        session.add(User(username=normalized, password_hash=_hash_password(password), email=normalized_email))
    return normalized


def authenticate(username: str, password: str) -> str | None:
    normalized = normalize_username(username)
    if USERNAME and PASSWORD and secrets.compare_digest(normalized, normalize_username(USERNAME)):
        if secrets.compare_digest(password, PASSWORD):
            return "__owner__"
        return None
    with SessionLocal() as session:
        account = session.get(User, normalized)
    if account and _verify_password(password, account.password_hash):
        return normalized
    return None


def require_auth(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _find_username_by_email(email: str) -> str | None:
    normalized_email = normalize_email(email)
    with SessionLocal() as session:
        return session.scalar(select(User.username).where(User.email == normalized_email))


def _hash_reset_code(username: str, code: str) -> str:
    # Keyed by username so a code for one account can't be replayed on another.
    return hashlib.sha256(f"{username}:{code}".encode()).hexdigest()


def create_reset_code(email: str) -> tuple[str, str] | None:
    """Generate a 6-digit reset code for the account matching this email.

    Returns (username, code) so the caller can display the code directly on
    the page — no email is sent. Returns None if no account matches the
    email address given.
    """
    username = _find_username_by_email(email)
    if not username:
        return None
    code = f"{secrets.randbelow(1_000_000):06d}"
    with SessionLocal.begin() as session:
        reset = session.get(PasswordReset, username)
        if reset is None:
            session.add(PasswordReset(username=username, code_hash=_hash_reset_code(username, code), expires=time.time() + RESET_CODE_TTL_SECONDS, attempts=0))
        else:
            reset.code_hash = _hash_reset_code(username, code)
            reset.expires = time.time() + RESET_CODE_TTL_SECONDS
            reset.attempts = 0
    return username, code


def consume_reset_code(username: str, code: str, new_password: str) -> bool:
    if len(new_password) < PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 8 characters")

    normalized = normalize_username(username)
    with SessionLocal.begin() as session:
        entry = session.get(PasswordReset, normalized)
        if not entry or entry.expires < time.time():
            return False

        # Cap guesses since a 6-digit code only has 1,000,000 combinations —
        # far weaker than the old 32-byte token, so brute-force protection matters here.
        if entry.attempts >= RESET_CODE_MAX_ATTEMPTS:
            session.delete(entry)
            return False

        if not hmac.compare_digest(_hash_reset_code(normalized, code), entry.code_hash):
            entry.attempts += 1
            return False

        account = session.get(User, normalized)
        if account is None:
            return False
        account.password_hash = _hash_password(new_password)
        session.delete(entry)
        return True
