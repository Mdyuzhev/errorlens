"""External integrations endpoints (TestIt, etc.)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.generators.testit import TestItGenerator
from app.integrations.testit_client import TestItStep, TestItTestCase, testit_client
from app.middleware.jwt_auth import require_auth
from app.models.db_models import Session
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/testit/status")
async def testit_status(_: User = Depends(require_auth)):
    """Check TestIt connection status."""
    if not settings.testit_enabled:
        return {"enabled": False}

    status = await testit_client.check_connection()
    return {"enabled": True, **status}


@router.post("/sessions/{session_id}/send-to-testit")
async def send_session_to_testit(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
):
    """Send session directly to TestIt as a test case."""
    if not settings.testit_enabled:
        raise HTTPException(status_code=400, detail="TestIt integration is disabled")

    result = await db.execute(
        select(Session)
        .options(selectinload(Session.data), selectinload(Session.analysis))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = {
        "url": session.url,
        "console_logs": session.data.console_logs if session.data else [],
        "network_errors": session.data.network_errors if session.data else [],
        "js_exceptions": session.data.js_exceptions if session.data else [],
        "recorded_requests": session.data.recorded_requests if session.data else [],
    }

    analysis = None
    if session.analysis:
        analysis = {
            "summary": session.analysis.summary,
            "probable_cause": session.analysis.probable_cause,
            "suggested_fix": session.analysis.suggested_fix,
        }

    generator = TestItGenerator(session_data, analysis)
    tc = generator.generate()

    steps = [
        TestItStep(
            action=step["action"],
            expected=step["expected"],
            test_data=step.get("testData", ""),
        )
        for step in tc["steps"]
    ]

    test_case = TestItTestCase(
        name=tc["name"],
        description=tc["description"],
        preconditions=tc["preconditions"],
        postconditions=tc["postconditions"],
        priority=tc["priority"],
        state="Ready",
        steps=steps,
        tags=tc["tags"] + ["errorlens", "auto-generated"],
    )

    result = await testit_client.create_test_case(test_case)

    if result.get("success"):
        session.testit_url = result["url"]
        session.testit_id = result["globalId"]
        await db.commit()

        logger.info(f"Created test case in TestIt: {result['url']}")
        return {
            "success": True,
            "message": "Test case created in TestIt",
            "testit_url": result["url"],
            "testit_id": result["globalId"],
        }
    else:
        logger.error(f"Failed to create test case in TestIt: {result.get('error')}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test case: {result.get('error')}",
        )
