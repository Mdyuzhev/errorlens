"""ErrorLens API - FastAPI entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker, get_db, init_db

# Import models to register them with Base.metadata before create_all
import app.models  # noqa: F401
from app.routers import (
    admin,
    analysis,
    article_folders,
    article_images,
    articles,
    auth,
    automations,
    entity_links,
    exports,
    generation,
    gitlab_connections,
    integrations,
    jql,
    launches,
    notifications,
    projects,
    saved_filters,
    sessions,
    task_settings,
    task_workflow,
    tasks,
    test_plans,
    testcase_folders,
    testcases,
    testruns,
    tests,
)
from app.services.auth import init_admin_user
from app.services.redis_client import close_redis, get_redis
from app.services.seed_demo import seed_demo_data
from app.services.seed_test_users import seed_test_users
from app.websocket import ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis
    try:
        await get_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    async with async_session_maker() as db:
        try:
            await init_admin_user(db)
            logger.info("Admin/demo users initialized")
        except Exception as e:
            logger.error(f"Failed to init users: {e}")

    # Seed demo data (articles, testcases, tasks)
    try:
        await seed_demo_data()
        logger.info("Demo data seeded")
    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")

    # Seed test users (owner1, owner2, member1, member2, etc.) for QA testing
    async with async_session_maker() as db:
        try:
            result = await seed_test_users(db)
            logger.info(f"Test users seeded: {result['users_created'] or 'all exist'}")
            logger.info(f"Test projects seeded: {result['projects_created'] or 'all exist'}")
        except Exception as e:
            logger.error(f"Failed to seed test users: {e}")

    yield

    # Shutdown Redis
    await close_redis()
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
app.include_router(testcase_folders.router)  # Must be before testcases (path conflict)
app.include_router(testcase_folders.move_router)  # /testcases/{id}/move-to-folder
app.include_router(testcases.router)
app.include_router(jql.router)  # EL023: JQL endpoints (before tasks for /tasks/jql-* priority)
app.include_router(tasks.router)
app.include_router(task_workflow.router)  # EL-FIX-025: workflow endpoints split from tasks
app.include_router(task_settings.router)  # EL019: Task workflow settings
app.include_router(article_folders.router)  # Must be before articles (path conflict)
app.include_router(article_folders.move_router)  # /articles/{id}/move-to-folder
app.include_router(article_images.router)  # /articles/images/* — before articles
app.include_router(article_images.list_router)  # /articles/{id}/images
app.include_router(articles.router)
app.include_router(entity_links.router)
app.include_router(testruns.router)
app.include_router(exports.router)
app.include_router(tests.router)
app.include_router(integrations.router)
app.include_router(analysis.router)
app.include_router(projects.router)
app.include_router(test_plans.router)
app.include_router(generation.router)  # Wave 4.0: Generation API
app.include_router(notifications.router)  # EL018: Notifications
app.include_router(gitlab_connections.router)  # EL020: GitLab Integration
app.include_router(launches.router)  # EL022: Launch upload from CI
app.include_router(saved_filters.router)  # EL023: JQL saved filters
app.include_router(automations.router)  # EL025: Task Automations
app.include_router(ws_router)  # Wave 4.0: WebSocket

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
            headers={"Cache-Control": "no-cache"},
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


@app.post("/debug/echo")
async def debug_echo(request: Request):
    """Debug endpoint to echo request body."""
    try:
        body = await request.json()
        logger.info(f"[DEBUG] Echo received: {str(body)[:500]}")
        return {"received": body, "content_type": request.headers.get("content-type")}
    except Exception as e:
        logger.error(f"[DEBUG] Echo error: {e}")
        return {"error": str(e)}
