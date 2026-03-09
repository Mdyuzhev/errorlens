"""Redis Streams helper for inter-service messaging."""
import logging
from dataclasses import dataclass
from typing import Any

from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

STREAM_GENERATION = "el:stream:generation"
STREAM_ANALYSIS = "el:stream:analysis"


@dataclass
class StreamMessage:
    id: str
    data: dict[str, Any]


async def publish(stream: str, data: dict[str, Any]) -> str:
    """Add message to stream, return message id."""
    r = await get_redis()
    msg_id = await r.xadd(stream, data)
    logger.debug(f"Published to {stream}: {msg_id}")
    return msg_id


async def create_group(stream: str, group: str) -> None:
    """Create consumer group if not exists."""
    r = await get_redis()
    try:
        await r.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info(f"Created consumer group {group} on {stream}")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.debug(f"Consumer group {group} already exists on {stream}")
        else:
            raise


async def consume(
    stream: str, group: str, consumer: str, count: int = 1
) -> list[StreamMessage]:
    """Read messages from stream via consumer group."""
    r = await get_redis()
    results = await r.xreadgroup(group, consumer, {stream: ">"}, count=count, block=5000)
    messages = []
    for _stream_name, entries in results:
        for msg_id, data in entries:
            messages.append(StreamMessage(id=msg_id, data=data))
    return messages


async def ack(stream: str, group: str, msg_id: str) -> None:
    """Acknowledge message processing."""
    r = await get_redis()
    await r.xack(stream, group, msg_id)
