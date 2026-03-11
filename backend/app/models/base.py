"""Base model and utilities."""

import uuid

from app.database import Base  # noqa: F401 — re-exported via __init__


def generate_uuid() -> str:
    """Generate UUID string for primary keys."""
    return str(uuid.uuid4())
