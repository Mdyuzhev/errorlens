"""Test generation service."""
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generators.inputs import HARInput, SwaggerInput
from app.generators.llm_generator import GenerationResult, LLMTestGenerator
from app.models.db_models import Session
from app.websocket.manager import manager

RESULT_TTL = 3600  # 1 hour
MAX_RESULTS = 1000


@dataclass
class TaskConfig:
    input_type: str
    input_data: Any
    framework: str
    provider: str
    model: str | None


@dataclass
class StoredResult:
    result: GenerationResult
    created_at: float = field(default_factory=time.time)


_tasks: dict[str, TaskConfig] = {}
_results: dict[str, StoredResult] = {}


def _cleanup_expired_results() -> None:
    """Remove expired results from cache."""
    cutoff = time.time() - RESULT_TTL
    expired = [k for k, v in _results.items() if v.created_at < cutoff]
    for k in expired:
        del _results[k]
    # Also enforce max size
    if len(_results) > MAX_RESULTS:
        sorted_items = sorted(_results.items(), key=lambda x: x[1].created_at)
        to_remove = len(_results) - MAX_RESULTS
        for k, _ in sorted_items[:to_remove]:
            del _results[k]


class GenerationService:
    @staticmethod
    async def create_task(input_type: str, input_data: Any, framework: str = "pytest",
                          provider: str = "anthropic", model: str | None = None) -> str:
        """Create new generation task."""
        task_id = str(uuid.uuid4())
        _tasks[task_id] = TaskConfig(input_type, input_data, framework, provider, model)
        return task_id

    @staticmethod
    async def run_task(task_id: str) -> GenerationResult | None:
        """Execute generation task with WebSocket progress."""
        config = _tasks.get(task_id)
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
                framework=config.framework
            )

            # Send started event
            endpoints = input_source.to_endpoints()
            await manager.send_started(task_id, len(endpoints))

            # Progress callback
            async def progress_cb(current: int, total: int, endpoint: str, log: str | None):
                await manager.send_progress(task_id, current, total, endpoint, log)

            # Generate tests
            result = await generator.generate(input_source, progress_cb)

            # Store result with TTL cleanup
            _cleanup_expired_results()
            result_id = str(uuid.uuid4())
            _results[result_id] = StoredResult(result=result)

            # Send completion
            await manager.send_completed(task_id, result_id)
            return result

        except Exception as e:
            await manager.send_error(task_id, str(e))
            return None
        finally:
            _tasks.pop(task_id, None)

    @staticmethod
    def get_result(result_id: str) -> GenerationResult | None:
        """Get stored generation result."""
        stored = _results.get(result_id)
        if stored:
            return stored.result
        return None

    @staticmethod
    def cleanup_results() -> int:
        """Manual cleanup of expired results. Returns count removed."""
        before = len(_results)
        _cleanup_expired_results()
        return before - len(_results)

    @staticmethod
    async def create_task_from_session(
        session_id: str,
        db: AsyncSession,
        framework: str = "pytest",
        provider: str = "anthropic",
        model: str | None = None
    ) -> str:
        """Load session, extract recorded_requests, create task."""
        # Load session from DB
        query = select(Session).where(Session.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Lazy-load session data
        await db.refresh(session, ["data"])

        if not session.data or not session.data.recorded_requests:
            raise HTTPException(status_code=400, detail="Session has no recorded requests")

        # Convert to HARInput format
        recorded_requests = session.data.recorded_requests
        if isinstance(recorded_requests, list):
            har_data = [
                {
                    "request": {
                        "url": req.get("url", ""),
                        "method": req.get("method", "GET"),
                        "headers": req.get("headers", {}),
                        "body": req.get("body")
                    }
                }
                for req in recorded_requests
            ]
        else:
            har_data = []

        # Create task
        task_id = await GenerationService.create_task(
            input_type="har",
            input_data=har_data,
            framework=framework,
            provider=provider,
            model=model
        )
        return task_id
