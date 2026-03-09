"""Generator worker — consumes tasks from Redis Streams."""
import asyncio
import json
import logging
import uuid

from app.services.generation_service import GenerationService
from app.services.redis_client import get_redis
from app.services.redis_streams import (
    STREAM_GENERATION,
    ack,
    consume,
    create_group,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_GROUP = "generators"
CONSUMER_NAME = f"worker-{uuid.uuid4().hex[:8]}"


async def handle_generation_task(task_id: str) -> None:
    """Process a single generation task."""
    config = await GenerationService.get_task_config(task_id)
    if not config:
        logger.error(f"Task {task_id} not found in Redis")
        return

    try:
        result = await GenerationService.run_task_internal(task_id, config)

        result_id = str(uuid.uuid4())
        await GenerationService.store_result(result_id, result)

        r = await get_redis()
        await r.publish(
            f"el:ws:{task_id}",
            json.dumps({"type": "completed", "result_id": result_id}),
        )
        logger.info(f"Task {task_id} completed → result {result_id}")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        r = await get_redis()
        await r.publish(
            f"el:ws:{task_id}",
            json.dumps({"type": "error", "message": str(e)}),
        )
    finally:
        r = await get_redis()
        await r.delete(f"el:task:{task_id}")


async def main() -> None:
    """Worker main loop."""
    logger.info(f"Generator worker starting: {CONSUMER_NAME}")

    await get_redis()
    await create_group(STREAM_GENERATION, CONSUMER_GROUP)

    logger.info(f"Listening on stream {STREAM_GENERATION}")

    while True:
        try:
            messages = await consume(
                STREAM_GENERATION, CONSUMER_GROUP, CONSUMER_NAME, count=1
            )
            for msg in messages:
                task_id = msg.data.get("task_id", "")
                if not task_id:
                    logger.warning(f"Message {msg.id} has no task_id, skipping")
                    await ack(STREAM_GENERATION, CONSUMER_GROUP, msg.id)
                    continue

                logger.info(f"Processing task {task_id}")
                await handle_generation_task(task_id)
                await ack(STREAM_GENERATION, CONSUMER_GROUP, msg.id)

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
