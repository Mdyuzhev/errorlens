"""Launches API - upload allure test results from CI/CD."""

import io
import json
import zipfile
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.testrun_service import TestRunService

router = APIRouter(prefix="/v1/launches", tags=["launches"])


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
