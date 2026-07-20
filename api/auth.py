import os
import secrets

from fastapi import HTTPException, Request

USERNAME = os.environ.get("APP_USERNAME", "")
PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-insecure-change-in-production")


def is_enabled() -> bool:
    return bool(USERNAME and PASSWORD)


def require_auth(request: Request) -> None:
    if not is_enabled():
        return
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")


def verify_credentials(username: str, password: str) -> bool:
    return secrets.compare_digest(username, USERNAME) and secrets.compare_digest(
        password, PASSWORD
    )
