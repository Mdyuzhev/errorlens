"""ErrorLens API - FastAPI entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import async_session_maker, get_db, init_db
# Import models to register them with Base.metadata before create_all
from app.models import db_models, user  # noqa: F401
from app.routers import (
    admin,
    auth,
    sessions,
    testcases,
    tasks,
    articles,
    testruns,
    exports,
    tests,
    integrations,
    analysis,
    projects,
)
from app.services.auth import init_admin_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    async with async_session_maker() as db:
        try:
            await init_admin_user(db)
            logger.info("Admin/demo users initialized")
        except Exception as e:
            logger.error(f"Failed to init users: {e}")

    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="ErrorLens API",
    description="AI-powered error analysis for QA engineers",
    version=settings.version,
    lifespan=lifespan,
)

# CORS: allow all origins (bookmarklet runs on any domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(testcases.router)
app.include_router(tasks.router)
app.include_router(articles.router)
app.include_router(testruns.router)
app.include_router(exports.router)
app.include_router(tests.router)
app.include_router(integrations.router)
app.include_router(analysis.router)
app.include_router(projects.router)

# Static files setup
DASHBOARD_PATH = None
BOOKMARKLET_PATH = None

for p in [
    Path("/app/dashboard-vue/dist"),
    Path(__file__).parent.parent.parent / "dashboard-vue" / "dist",
    Path(__file__).parent.parent.parent / "dashboard",
]:
    if p.exists() and (p / "index.html").exists():
        DASHBOARD_PATH = p
        if (p / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(p / "assets")), name="assets")
        logger.info(f"Serving dashboard from {p}")
        break

for p in [
    Path("/app/bookmarklet"),
    Path(__file__).parent.parent.parent / "bookmarklet",
]:
    if p.exists() and (p / "recorder.js").exists():
        BOOKMARKLET_PATH = p
        app.mount("/bookmarklet", StaticFiles(directory=str(p)), name="bookmarklet")
        logger.info(f"Serving bookmarklet from {p}")
        break


@app.get("/go_to_test.js")
async def bookmarklet_shortcut():
    """Short URL for bookmarklet script."""
    if BOOKMARKLET_PATH:
        return FileResponse(
            BOOKMARKLET_PATH / "recorder.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"}
        )
    raise HTTPException(status_code=404, detail="Bookmarklet not found")


@app.get("/")
async def serve_spa_root():
    """Serve the SPA index.html at root."""
    if DASHBOARD_PATH:
        return FileResponse(DASHBOARD_PATH / "index.html")
    return {"message": "ErrorLens API", "docs": "/docs"}


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": settings.version}


@app.get("/debug/users")
async def debug_users(db: AsyncSession = Depends(get_db)):
    """Debug endpoint to check users in DB."""
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"count": len(users), "usernames": [u.username for u in users]}
