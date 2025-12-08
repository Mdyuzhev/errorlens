"""Test generation service."""
import uuid
from dataclasses import dataclass
from typing import Any

from app.generators.llm_generator import LLMTestGenerator, GenerationResult
from app.generators.inputs import SwaggerInput, HARInput
from app.websocket.manager import manager


@dataclass
class TaskConfig:
    input_type: str
    input_data: Any
    framework: str
    provider: str
    model: str | None


_tasks: dict[str, TaskConfig] = {}
_results: dict[str, GenerationResult] = {}


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

            # Store result
            result_id = str(uuid.uuid4())
            _results[result_id] = result

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
        return _results.get(result_id)
