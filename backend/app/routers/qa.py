"""QA dashboard router."""

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.testcase import TestCase
from app.models.testplan import TestPlanRunResult
from app.models.user import User
from app.services.redis_client import get_redis

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])

CACHE_TTL = 300


@router.get("/dashboard")
async def get_qa_dashboard(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """QA dashboard with Redis cache."""
    cache_key = f"qa:dashboard:{project_id}"
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return JSONResponse(content=json.loads(cached), headers={"X-Cache": "HIT"})
    except Exception:
        pass

    result = await db.execute(
        select(TestCase.status, func.count(TestCase.id).label("count"))
        .where(TestCase.project_id == project_id)
        .group_by(TestCase.status)
    )
    by_status = [{"status": r.status, "count": r.count} for r in result.all()]

    result2 = await db.execute(
        select(TestCase.id, TestCase.title, func.count(TestPlanRunResult.id).label("failed_count"))
        .join(TestPlanRunResult, TestPlanRunResult.testcase_id == TestCase.id)
        .where(TestCase.project_id == project_id, TestPlanRunResult.status == "failed")
        .group_by(TestCase.id, TestCase.title)
        .order_by(func.count(TestPlanRunResult.id).desc())
        .limit(5)
    )
    top_failed = [{"id": r.id, "title": r.title, "failed_count": r.failed_count} for r in result2.all()]

    data = {"by_status": by_status, "top_failed": top_failed}

    try:
        redis = await get_redis()
        await redis.setex(cache_key, CACHE_TTL, json.dumps(data))
    except Exception:
        pass

    return JSONResponse(content=data, headers={"X-Cache": "MISS"})
