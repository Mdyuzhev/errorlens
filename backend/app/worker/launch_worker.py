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


async def handle_launch(launch_id: str, project_id: str) -> None:
    """Notify UI that a new launch is available."""
    try:
        r = await get_redis()
        channel = f"el:ws:launches:{project_id}" if project_id else "el:ws:launches:all"
        await r.publish(channel, json.dumps({
            "type": "launch_created",
            "launch_id": launch_id,
            "project_id": project_id,
        }))
        logger.info(f"Notified UI: launch {launch_id} for project {project_id}")
    except Exception as e:
        logger.error(f"Failed to notify UI for launch {launch_id}: {e}")


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
                launch_id = msg.data.get("launch_id", "")
                project_id = msg.data.get("project_id", "")
                await handle_launch(launch_id, project_id)
                await ack(STREAM_LAUNCHES, CONSUMER_GROUP, msg.id)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
