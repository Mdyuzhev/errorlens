"""Authentication helpers."""

from fastapi import Request

from app.config import settings


async def check_admin_key(request: Request) -> bool:
    """Check if request has valid admin key."""
    admin_key = request.headers.get("X-Admin-Key")
    if admin_key and admin_key == settings.admin_key:
        return True
    return False


async def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
