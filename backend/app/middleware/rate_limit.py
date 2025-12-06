"""Rate limiting middleware."""

from collections import defaultdict
from datetime import date

from fastapi import HTTPException, Request

from app.config import settings

from .auth import check_admin_key, get_client_ip

# Simple in-memory store (replace with Redis for production)
request_counts: dict[str, dict[date, int]] = defaultdict(lambda: defaultdict(int))


async def rate_limit_middleware(request: Request) -> int:
    """
    Check rate limits. Admins bypass limits.

    Returns remaining requests for the day.
    """
    if await check_admin_key(request):
        return -1  # Admin - unlimited

    client_ip = await get_client_ip(request)
    today = date.today()

    current_count = request_counts[client_ip][today]

    if current_count >= settings.rate_limit_per_day:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Лимит исчерпан. Максимум {settings.rate_limit_per_day} запросов в день.",
                "limit": settings.rate_limit_per_day,
                "reset": "midnight",
            },
        )

    request_counts[client_ip][today] += 1
    remaining = settings.rate_limit_per_day - request_counts[client_ip][today]

    return remaining
