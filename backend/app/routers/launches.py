"""Launches API - upload allure test results from CI/CD."""

import io
import json
import logging
import zipfile
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.testrun_service import TestRunService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/launches", tags=["launches"])


class StepSchema(BaseModel):
    name: str
    status: str = "passed"
    duration_ms: int = 0
    parameters: list[dict] = []
    steps: list["StepSchema"] = []
    attachments: list[dict] = []
    status_details: dict = {}
    description: str = ""

StepSchema.model_rebuild()

class TestResultSchema(BaseModel):
    name: str
    full_name: str = ""
    status: str
    duration_ms: int = 0
    markers: list[str] = []
    parameters: list[dict] = []
    feature: str = ""
    story: str = ""
    severity: str = "normal"
    links: list[dict] = []
    steps: list[StepSchema] = []
    attachments: list[dict] = []
    status_details: dict = {}
    # --- New fields v2.0 ---
    title: str = ""
    description: str = ""
    epic: str = ""
    suite: str = ""
    parent_suite: str = ""
    tags: list[str] = []
    owner: str = ""
    test_id: str = ""
    flaky: bool = False
    known_issue: str = ""
    retry_count: int = 0

class IngestRequest(BaseModel):
    launch_name: str = "Unnamed launch"
    branch: str = ""
    environment: str = ""
    pipeline_id: str = ""
    project_id: str = ""
    tests: list[TestResultSchema]


def _parse_allure_results(zip_data: bytes) -> dict[str, Any]:
    """Parse allure-results ZIP and extract test data."""
    tests: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    skipped = 0
    broken = 0

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        for name in zf.namelist():
            if not name.endswith("-result.json"):
                continue
            try:
                data = json.loads(zf.read(name))
            except (json.JSONDecodeError, KeyError):
                continue

            status = data.get("status", "unknown")
            if status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
            elif status == "skipped":
                skipped += 1
            elif status == "broken":
                broken += 1
                failed += 1  # count broken as failed

            test_entry: dict[str, Any] = {
                "name": data.get("name", name),
                "fullName": data.get("fullName", ""),
                "status": status,
                "duration_ms": data.get("time", {}).get("duration", 0),
                "statusDetails": data.get("statusDetails", {}),
            }

            # Extract labels (feature, story, severity)
            labels = {
                label["name"]: label["value"]
                for label in data.get("labels", [])
                if "name" in label and "value" in label
            }
            test_entry["feature"] = labels.get("feature", "")
            test_entry["story"] = labels.get("story", "")
            test_entry["severity"] = labels.get("severity", "normal")

            # Extract steps with details
            raw_steps = data.get("steps", [])
            test_entry["steps_count"] = len(raw_steps)
            test_entry["steps"] = [
                {
                    "name": s.get("name", ""),
                    "status": s.get("status", "unknown"),
                    "duration_ms": s.get("time", {}).get("duration", 0),
                    "statusDetails": s.get("statusDetails", {}),
                }
                for s in raw_steps
            ]

            # Extract attachments info
            raw_attachments = data.get("attachments", [])
            test_entry["attachments_count"] = len(raw_attachments)
            test_entry["attachments"] = [
                {
                    "name": a.get("name", ""),
                    "type": a.get("type", ""),
                    "source": a.get("source", ""),
                }
                for a in raw_attachments
            ]

            tests.append(test_entry)

    return {
        "tests": tests,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "broken": broken,
        "total": len(tests),
    }


@router.post("/upload")
async def upload_launch(
    file: UploadFile = File(...),
    name: str = Form("Unnamed launch"),
    branch: str = Form(""),
    environment: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
) -> dict[str, Any]:
    """Upload allure-results ZIP and create a test run.

    Used by GitLab CI job `upload_to_errorlens`.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip file")

    zip_data = await file.read()
    if len(zip_data) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    try:
        parsed = _parse_allure_results(zip_data)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    if parsed["total"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No allure result files found in ZIP",
        )

    # Determine overall status
    overall_status = "passed" if parsed["failed"] == 0 else "failed"

    # Create TestRun via existing service
    service = TestRunService(db)
    run = await service.create_run(test_type="e2e", total_tests=parsed["total"])

    # Finish immediately with parsed results
    run = await service.finish_run(
        run_id=run.id,
        status=overall_status,
        passed=parsed["passed"],
        failed=parsed["failed"],
        skipped=parsed["skipped"],
        results=parsed["tests"],
        output=json.dumps({
            "launch_name": name,
            "branch": branch,
            "environment": environment,
            "broken": parsed["broken"],
            "uploaded_by": user.username,
            "uploaded_at": datetime.utcnow().isoformat(),
        }),
    )

    return {
        "id": run.id,
        "name": name,
        "status": overall_status,
        "total": parsed["total"],
        "passed": parsed["passed"],
        "failed": parsed["failed"],
        "skipped": parsed["skipped"],
        "broken": parsed["broken"],
    }


@router.post("/ingest")
async def ingest_launch(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
) -> dict[str, Any]:
    """Accept native errorlens-pytest plugin report (batch mode)."""
    if not request.tests:
        raise HTTPException(status_code=400, detail="tests list is empty")

    passed = sum(1 for t in request.tests if t.status == "passed")
    failed = sum(1 for t in request.tests if t.status in ("failed", "broken"))
    skipped = sum(1 for t in request.tests if t.status == "skipped")
    overall = "passed" if failed == 0 else "failed"

    service = TestRunService(db)
    run = await service.create_run(test_type="e2e", total_tests=len(request.tests))

    results = [t.model_dump() for t in request.tests]

    run = await service.finish_run(
        run_id=run.id,
        status=overall,
        passed=passed,
        failed=failed,
        skipped=skipped,
        results=results,
        output=None,
    )

    # Save metadata (new fields from task-01 migration)
    try:
        run.launch_name = request.launch_name
        run.branch = request.branch
        run.environment = request.environment
        run.pipeline_id = request.pipeline_id
        run.source = "plugin"
        await db.commit()
    except Exception:
        pass  # fields not yet added by migration

    # Publish to Redis Stream
    await _publish_launch_event(run.id, request.project_id, "launch_completed")

    return {
        "id": run.id,
        "status": overall,
        "total": len(request.tests),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }


# --- Streaming API: start → batch → finish ---


class StartRequest(BaseModel):
    launch_name: str = "Unnamed launch"
    branch: str = ""
    environment: str = ""
    pipeline_id: str = ""
    project_id: str = ""
    total_expected: int = 0


class BatchRequest(BaseModel):
    launch_id: str
    project_id: str = ""
    tests: list[TestResultSchema]


class FinishRequest(BaseModel):
    launch_id: str
    project_id: str = ""


@router.post("/ingest/start")
async def ingest_start(
    request: StartRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
) -> dict[str, Any]:
    """Start a streaming launch. Returns launch_id for subsequent batches."""
    service = TestRunService(db)
    run = await service.create_run(
        test_type="e2e",
        total_tests=request.total_expected,
        status="running",
    )

    try:
        run.launch_name = request.launch_name
        run.branch = request.branch
        run.environment = request.environment
        run.pipeline_id = request.pipeline_id
        run.source = "plugin"
        await db.commit()
    except Exception:
        pass

    await _publish_launch_event(
        run.id, request.project_id, "launch_started",
        total=request.total_expected,
        launch_name=request.launch_name,
        branch=request.branch,
        environment=request.environment,
    )

    return {"launch_id": run.id}


@router.post("/ingest/batch")
async def ingest_batch(
    request: BatchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
) -> dict[str, Any]:
    """Append a batch of test results to a running launch."""
    if not request.tests:
        raise HTTPException(status_code=400, detail="tests list is empty")

    service = TestRunService(db)
    run = await service.get_run(request.launch_id)
    if not run:
        raise HTTPException(status_code=404, detail="launch not found")

    new_results = [t.model_dump() for t in request.tests]
    existing = run.results or []
    run.results = existing + new_results

    # Update counters
    batch_passed = sum(1 for t in request.tests if t.status == "passed")
    batch_failed = sum(1 for t in request.tests if t.status in ("failed", "broken"))
    batch_skipped = sum(1 for t in request.tests if t.status == "skipped")

    run.passed = (run.passed or 0) + batch_passed
    run.failed = (run.failed or 0) + batch_failed
    run.skipped = (run.skipped or 0) + batch_skipped
    run.total_tests = (run.total_tests or 0) + len(request.tests)
    await db.commit()

    await _publish_launch_event(
        run.id, request.project_id, "launch_batch",
        tests=new_results,
        passed=run.passed,
        failed=run.failed,
        skipped=run.skipped,
        total=run.total_tests,
    )

    return {
        "launch_id": run.id,
        "batch_size": len(request.tests),
        "total": run.total_tests,
        "passed": run.passed,
        "failed": run.failed,
        "skipped": run.skipped,
    }


@router.post("/ingest/finish")
async def ingest_finish(
    request: FinishRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
) -> dict[str, Any]:
    """Finalize a streaming launch."""
    service = TestRunService(db)
    run = await service.get_run(request.launch_id)
    if not run:
        raise HTTPException(status_code=404, detail="launch not found")

    run.status = "passed" if (run.failed or 0) == 0 else "failed"
    run.finished_at = datetime.utcnow()
    if run.started_at:
        run.duration_ms = int(
            (run.finished_at - run.started_at).total_seconds() * 1000
        )
    await db.commit()

    await _publish_launch_event(
        run.id, request.project_id, "launch_completed",
        status=run.status,
        passed=run.passed,
        failed=run.failed,
        skipped=run.skipped,
        total=run.total_tests,
        duration_ms=run.duration_ms,
    )

    return {
        "launch_id": run.id,
        "status": run.status,
        "total": run.total_tests,
        "passed": run.passed,
        "failed": run.failed,
        "skipped": run.skipped,
        "duration_ms": run.duration_ms,
    }


async def _publish_launch_event(
    launch_id: str, project_id: str, event_type: str, **extra
) -> None:
    """Publish launch event to Redis Stream."""
    try:
        from app.services.redis_streams import STREAM_LAUNCHES, publish
        await publish(STREAM_LAUNCHES, {
            "launch_id": launch_id,
            "project_id": project_id,
            "event": event_type,
            **{k: json.dumps(v) if isinstance(v, (list, dict)) else str(v) for k, v in extra.items()},
        })
    except Exception as e:
        logger.warning(f"Redis stream publish failed: {e}")
