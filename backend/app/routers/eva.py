"""EVA v2.1 — test quality analysis endpoint."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.models.user import User
from app.services.auth import require_auth
from app.services.eva_service import EvaService

router = APIRouter(prefix="/api/v1/generator/eva", tags=["eva"])


@router.post("/analyze")
async def analyze_tests(
    file: UploadFile = File(...),
    current_user: User = Depends(require_auth),
) -> dict:
    """Analyse a ZIP of test files and return EVA quality score."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, "Expected .zip file")
    zip_data = await file.read()
    if len(zip_data) > 50 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 50MB)")
    result = EvaService.analyse_zip(zip_data)
    return asdict(result)
