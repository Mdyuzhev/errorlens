"""Launch worker — consumes el:stream:launches and notifies UI via Pub/Sub."""
import asyncio
import json
import logging
import uuid

from app.services.redis_client import get_redis
from app.services.redis_streams import (
    STREAM_LAUNCHES,
    ack,
    consume,
    create_group,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_GROUP = "launches"
CONSUMER_NAME = f"launch-worker-{uuid.uuid4().hex[:8]}"


async def handle_launch(msg_data: dict) -> None:
    """Forward launch event to UI via Pub/Sub."""
    try:
        launch_id = msg_data.get("launch_id", "")
        project_id = msg_data.get("project_id", "")
        event = msg_data.get("event", "launch_created")

        r = await get_redis()

        # Publish to project-specific channel (ResultsView subscribes)
        channel = f"el:ws:launches:{project_id}" if project_id else "el:ws:launches:all"
        payload = {"type": event, "launch_id": launch_id, "project_id": project_id}

        # Forward extra fields from stream message
        for k, v in msg_data.items():
            if k not in ("launch_id", "project_id", "event"):
                try:
                    payload[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    payload[k] = v

        await r.publish(channel, json.dumps(payload))

        # Also publish to launch-specific channel (for WS per-launch)
        await r.publish(f"el:ws:launch:{launch_id}", json.dumps(payload))

        logger.info(f"Notified UI: {event} launch={launch_id}")
    except Exception as e:
        logger.error(f"Failed to notify UI: {e}")


async def main() -> None:
    """Worker main loop."""
    logger.info(f"Launch worker starting: {CONSUMER_NAME}")

    await get_redis()
    await create_group(STREAM_LAUNCHES, CONSUMER_GROUP)

    logger.info(f"Listening on stream: {STREAM_LAUNCHES}")

    while True:
        try:
            messages = await consume(STREAM_LAUNCHES, CONSUMER_GROUP, CONSUMER_NAME, count=10)
            for msg in messages:
                await handle_launch(msg.data)
                await ack(STREAM_LAUNCHES, CONSUMER_GROUP, msg.id)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
