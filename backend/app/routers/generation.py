"""Test generation API."""
import io
import json
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.generation_service import GenerationService
from app.services.redis_streams import STREAM_GENERATION, publish

router = APIRouter(prefix="/v1/generation", tags=["generation"])


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
async def generate_from_swagger(
    file: UploadFile = File(...),
    framework: str = Form("pytest"),
    provider: str = Form("anthropic"),
    model: str | None = Form(None),
):
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
    await publish(STREAM_GENERATION, {"task_id": task_id})
    return TaskResponse(task_id=task_id, websocket_url=f"/ws/generation/{task_id}")


@router.get("/result/{result_id}", response_model=ResultResponse)
async def get_result(result_id: str):
    """Get generation result by ID."""
    result = await GenerationService.get_result(result_id)
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
    result = await GenerationService.get_result(result_id)
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


@router.post("/from-session/{session_id}", response_model=TaskResponse)
async def generate_from_session(
    session_id: str,
    framework: str = Form("pytest"),
    provider: str = Form("anthropic"),
    model: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Generate tests from recorded browser session."""
    task_id = await GenerationService.create_task_from_session(
        session_id=session_id,
        db=db,
        framework=framework,
        provider=provider,
        model=model,
    )
    await publish(STREAM_GENERATION, {"task_id": task_id})
    return TaskResponse(task_id=task_id, websocket_url=f"/ws/generation/{task_id}")


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
