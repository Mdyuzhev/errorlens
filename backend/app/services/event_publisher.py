"""Event publisher — publishes domain events to Redis Streams."""

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.services import redis_streams

logger = logging.getLogger(__name__)

STREAM_EVENTS = "el:events"


async def publish(
    event_type: str,
    payload: dict[str, Any],
    actor_id: str | None = None,
    project_id: str | None = None,
) -> str | None:
    """Publish a domain event to el:events stream.

    Never raises exceptions — logs errors and returns None on failure.
    """
    event_id = str(uuid4())
    try:
        envelope = {
            "event_id": event_id,
            "type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "actor_id": actor_id or "",
            "project_id": project_id or "",
            "payload": json.dumps(payload, default=str),
        }
        await redis_streams.publish(STREAM_EVENTS, envelope)
        logger.info(f"Event published: {event_type} ({event_id[:8]})")
        return event_id
    except Exception as e:
        logger.error(f"Failed to publish event {event_type}: {e}")
        return None
