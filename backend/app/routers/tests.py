"""Test execution endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.generators import generate_pom_xml, generate_pytest_file, generate_restassured_file
from app.middleware.jwt_auth import require_auth
from app.models.db_models import Session
from app.models.user import User
from app.models_pydantic import RecordedHttpExchange, RunTestRequest
from app.test_runner import create_test_run, get_test_run, run_pytest, run_restassured

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post("/run")
async def start_test_run(
    request: RunTestRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> dict:
    """Start pytest execution."""
    test_id = create_test_run()

    if request.session_id:
        query = (
            select(Session)
            .options(selectinload(Session.data))
            .where(Session.id == request.session_id)
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session.data or not session.data.recorded_requests:
            raise HTTPException(status_code=400, detail="Session has no recorded requests")

        recorded = []
        for req_dict in session.data.recorded_requests:
            if isinstance(req_dict, dict):
                recorded.append(RecordedHttpExchange(**req_dict))
            else:
                recorded.append(req_dict)

        test_code = generate_pytest_file(recorded)

    elif request.test_code:
        test_code = request.test_code
    else:
        raise HTTPException(status_code=400, detail="Provide session_id or test_code")

    asyncio.create_task(run_pytest(test_code, test_id))

    logger.info(f"Started test run {test_id}")
    return {"test_id": test_id, "status": "started"}


@router.post("/run/restassured")
async def start_restassured_test_run(
    request: RunTestRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> dict:
    """Start REST Assured (Java/Maven) test execution."""
    test_id = create_test_run()

    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    query = (
        select(Session).options(selectinload(Session.data)).where(Session.id == request.session_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.data or not session.data.recorded_requests:
        raise HTTPException(status_code=400, detail="Session has no recorded requests")

    recorded = []
    for req_dict in session.data.recorded_requests:
        if isinstance(req_dict, dict):
            recorded.append(RecordedHttpExchange(**req_dict))
        else:
            recorded.append(req_dict)

    java_code = generate_restassured_file(recorded)
    pom_xml = generate_pom_xml()

    asyncio.create_task(run_restassured(java_code, pom_xml, test_id))

    logger.info(f"Started REST Assured test run {test_id}")
    return {"test_id": test_id, "status": "started"}


@router.get("/{test_id}/status")
async def get_test_status(
    test_id: str,
    _: User = Depends(require_auth),
) -> dict:
    """Get test run status and output."""
    result = get_test_run(test_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test run not found")
    return result
