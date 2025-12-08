"""Test generation API."""
import json
import io
import zipfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.generation_service import GenerationService

router = APIRouter(prefix="/api/v1/generation", tags=["generation"])


class TaskResponse(BaseModel):
    task_id: str
    websocket_url: str


class ResultResponse(BaseModel):
    total_endpoints: int
    successful: int
    failed: int
    errors: list[str]
    tests: list[dict]
    conftest: str | None


@router.post("/from-swagger", response_model=TaskResponse)
async def generate_from_swagger(background_tasks: BackgroundTasks,
                                file: UploadFile = File(...),
                                framework: str = Form("pytest"),
                                provider: str = Form("anthropic"),
                                model: str | None = Form(None)):
    """Generate tests from Swagger/OpenAPI spec."""
    content = await file.read()
    try:
        spec = json.loads(content)
    except json.JSONDecodeError:
        import yaml
        try:
            spec = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise HTTPException(400, f"Invalid file format: {e}")

    if "paths" not in spec:
        raise HTTPException(400, "Invalid Swagger: missing 'paths'")

    task_id = await GenerationService.create_task("swagger", spec, framework, provider, model)
    background_tasks.add_task(_delayed_run, task_id)
    return TaskResponse(task_id=task_id, websocket_url=f"/ws/generation/{task_id}")


@router.get("/result/{result_id}", response_model=ResultResponse)
async def get_result(result_id: str):
    """Get generation result by ID."""
    result = GenerationService.get_result(result_id)
    if not result:
        raise HTTPException(404, "Result not found")
    return ResultResponse(
        total_endpoints=result.total_endpoints,
        successful=result.successful,
        failed=result.failed,
        errors=result.errors,
        tests=[{"endpoint": t.endpoint, "code": t.code, "is_valid": t.is_valid, "error": t.validation_error} for t in result.tests],
        conftest=result.conftest,
    )


@router.get("/download/{result_id}")
async def download_result(result_id: str):
    """Download tests as ZIP archive."""
    result = GenerationService.get_result(result_id)
    if not result:
        raise HTTPException(404, "Result not found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if result.conftest:
            zf.writestr("conftest.py", result.conftest)
        for i, t in enumerate(result.tests):
            if t.is_valid and t.code:
                name = f"test_{t.endpoint.replace(' ', '_').replace('/', '_')}_{i}.py"
                zf.writestr(name, t.code)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename=tests_{result_id[:8]}.zip"})


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


async def _delayed_run(task_id: str):
    """Run task after small delay to ensure WS connection established."""
    import asyncio
    await asyncio.sleep(0.5)
    await GenerationService.run_task(task_id)
