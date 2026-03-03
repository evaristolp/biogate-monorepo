import os

from fastapi import Header, HTTPException


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """
    Placeholder auth dependency.

    If BIOGATE_API_KEY is set, require `Authorization: Bearer <key>` for protected routes.
    If unset, auth is effectively disabled (useful for local/dev and CI).
    """
    expected = os.getenv("BIOGATE_API_KEY")
    if not expected:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Missing Bearer token"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Invalid token"},
        )

