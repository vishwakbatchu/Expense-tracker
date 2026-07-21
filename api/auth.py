import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time

from fastapi import HTTPException, Request

from expense_tracker import storage

USERNAME = os.environ.get("APP_USERNAME", "")
PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-insecure-change-in-production")
USERS_FILE = os.path.join(os.environ.get("DATA_DIR", "."), "users.json")
RESETS_FILE = os.path.join(os.environ.get("DATA_DIR", "."), "password_resets.json")
USERNAME_PATTERN = re.compile(r"^[a-z0-9_-]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_ITERATIONS = 600_000
RESET_TOKEN_TTL_SECONDS = 30 * 60


def _load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as file:
        return json.load(file)


def _save_users(users):
    storage.atomic_write_json(USERS_FILE, users)


def _load_resets():
    if not os.path.exists(RESETS_FILE):
        return {}
    with open(RESETS_FILE, "r") as file:
        return json.load(file)


def _save_resets(resets):
    storage.atomic_write_json(RESETS_FILE, resets)


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
    if normalized in _load_users():
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
    users = _load_users()
    users[normalized] = {"password": _hash_password(password), "email": normalized_email}
    _save_users(users)
    return normalized


def authenticate(username: str, password: str) -> str | None:
    normalized = normalize_username(username)
    if USERNAME and PASSWORD and secrets.compare_digest(normalized, normalize_username(USERNAME)):
        if secrets.compare_digest(password, PASSWORD):
            return "__owner__"
        return None
    account = _load_users().get(normalized)
    if account and _verify_password(password, account.get("password", "")):
        return normalized
    return None


def require_auth(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _find_username_by_email(email: str) -> str | None:
    normalized_email = normalize_email(email)
    for uname, info in _load_users().items():
        if info.get("email", "") == normalized_email:
            return uname
    return None


def create_reset_token(email: str) -> tuple[str, str] | None:
    username = _find_username_by_email(email)
    if not username:
        return None
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    resets = _load_resets()
    resets[token_hash] = {"username": username, "expires": time.time() + RESET_TOKEN_TTL_SECONDS}
    _save_resets(resets)
    return username, token


def consume_reset_token(token: str, new_password: str) -> bool:
    if len(new_password) < PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 8 characters")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    resets = _load_resets()
    entry = resets.get(token_hash)
    if not entry or entry["expires"] < time.time():
        return False
    username = entry["username"]
    users = _load_users()
    if username not in users:
        return False
    users[username]["password"] = _hash_password(new_password)
    _save_users(users)
    del resets[token_hash]
    _save_resets(resets)
    return True
