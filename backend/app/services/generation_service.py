"""Test generation service with Redis-backed storage."""
import json
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generators.inputs import HARInput, SwaggerInput
from app.generators.llm_generator import GenerationResult, LLMTestGenerator
from app.models.db_models import Session
from app.services.redis_client import get_redis
from app.websocket.manager import manager

TASK_KEY = "el:task:{task_id}"
RESULT_KEY = "el:result:{result_id}"
TASK_TTL = 3600
RESULT_TTL = 3600


@dataclass
class TaskConfig:
    input_type: str
    input_data: Any
    framework: str
    provider: str
    model: str | None

    def to_json(self) -> str:
        return json.dumps({
            "input_type": self.input_type,
            "input_data": self.input_data,
            "framework": self.framework,
            "provider": self.provider,
            "model": self.model,
        })

    @classmethod
    def from_json(cls, data: str) -> "TaskConfig":
        d = json.loads(data)
        return cls(**d)


class GenerationService:
    @staticmethod
    async def create_task(
        input_type: str,
        input_data: Any,
        framework: str = "pytest",
        provider: str = "anthropic",
        model: str | None = None,
    ) -> str:
        """Create new generation task in Redis."""
        task_id = str(uuid.uuid4())
        config = TaskConfig(input_type, input_data, framework, provider, model)
        r = await get_redis()
        await r.setex(
            TASK_KEY.format(task_id=task_id), TASK_TTL, config.to_json()
        )
        return task_id

    @staticmethod
    async def get_task_config(task_id: str) -> TaskConfig | None:
        """Get task config from Redis."""
        r = await get_redis()
        data = await r.get(TASK_KEY.format(task_id=task_id))
        if data is None:
            return None
        return TaskConfig.from_json(data)

    @staticmethod
    async def run_task(task_id: str) -> GenerationResult | None:
        """Execute generation task with WebSocket progress."""
        config = await GenerationService.get_task_config(task_id)
        if not config:
            await manager.send_error(task_id, "Task not found")
            return None

        try:
            # Parse input
            if config.input_type == "swagger":
                input_source = SwaggerInput(config.input_data)
            else:
                input_source = HARInput(config.input_data)

            # Initialize generator
            generator = LLMTestGenerator(
                provider=config.provider,
                model=config.model,
                framework=config.framework,
            )

            # Send started event
            endpoints = input_source.to_endpoints()
            await manager.send_started(task_id, len(endpoints))

            # Progress callback
            async def progress_cb(
                current: int, total: int, endpoint: str, log: str | None
            ):
                await manager.send_progress(task_id, current, total, endpoint, log)

            # Generate tests
            result = await generator.generate(input_source, progress_cb)

            # Store result in Redis
            result_id = str(uuid.uuid4())
            await GenerationService.store_result(result_id, result)

            # Send completion
            await manager.send_completed(task_id, result_id)
            return result

        except Exception as e:
            await manager.send_error(task_id, str(e))
            return None
        finally:
            # Cleanup task from Redis
            r = await get_redis()
            await r.delete(TASK_KEY.format(task_id=task_id))

    @staticmethod
    async def run_task_internal(
        task_id: str, config: TaskConfig
    ) -> GenerationResult:
        """Run generation without WebSocket — for worker use."""
        if config.input_type == "swagger":
            input_source = SwaggerInput(config.input_data)
        else:
            input_source = HARInput(config.input_data)

        generator = LLMTestGenerator(
            provider=config.provider,
            model=config.model,
            framework=config.framework,
        )

        r = await get_redis()

        endpoints = input_source.to_endpoints()
        await r.publish(
            f"el:ws:{task_id}",
            json.dumps({"type": "started", "total": len(endpoints)}),
        )

        async def progress_cb(
            current: int, total: int, endpoint: str, log: str | None
        ):
            data: dict[str, Any] = {
                "type": "progress",
                "current": current,
                "total": total,
                "endpoint": endpoint,
            }
            if log:
                data["log"] = log
            await r.publish(f"el:ws:{task_id}", json.dumps(data))

        result = await generator.generate(input_source, progress_cb)
        return result

    @staticmethod
    async def store_result(result_id: str, result: GenerationResult) -> None:
        """Store generation result in Redis with TTL."""
        r = await get_redis()
        data = json.dumps({
            "total_endpoints": result.total_endpoints,
            "successful": result.successful,
            "failed": result.failed,
            "errors": result.errors,
            "tests": [
                {
                    "endpoint": t.endpoint,
                    "code": t.code,
                    "is_valid": t.is_valid,
                    "validation_error": t.validation_error,
                }
                for t in result.tests
            ],
            "conftest": result.conftest,
        })
        await r.setex(RESULT_KEY.format(result_id=result_id), RESULT_TTL, data)

    @staticmethod
    async def get_result(result_id: str) -> GenerationResult | None:
        """Get stored generation result from Redis."""
        r = await get_redis()
        data = await r.get(RESULT_KEY.format(result_id=result_id))
        if data is None:
            return None
        d = json.loads(data)
        from app.generators.llm_generator import GeneratedTest

        tests = [
            GeneratedTest(
                endpoint=t["endpoint"],
                code=t["code"],
                is_valid=t["is_valid"],
                validation_error=t.get("validation_error"),
            )
            for t in d["tests"]
        ]
        return GenerationResult(
            total_endpoints=d["total_endpoints"],
            successful=d["successful"],
            failed=d["failed"],
            errors=d["errors"],
            tests=tests,
            conftest=d.get("conftest"),
        )

    @staticmethod
    async def create_task_from_session(
        session_id: str,
        db: AsyncSession,
        framework: str = "pytest",
        provider: str = "anthropic",
        model: str | None = None,
    ) -> str:
        """Load session, extract recorded_requests, create task."""
        query = select(Session).where(Session.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await db.refresh(session, ["data"])

        if not session.data or not session.data.recorded_requests:
            raise HTTPException(
                status_code=400, detail="Session has no recorded requests"
            )

        recorded_requests = session.data.recorded_requests
        if isinstance(recorded_requests, list):
            har_data = [
                {
                    "request": {
                        "url": req.get("url", ""),
                        "method": req.get("method", "GET"),
                        "headers": req.get("headers", {}),
                        "body": req.get("body"),
                    }
                }
                for req in recorded_requests
            ]
        else:
            har_data = []

        task_id = await GenerationService.create_task(
            input_type="har",
            input_data=har_data,
            framework=framework,
            provider=provider,
            model=model,
        )
        return task_id
