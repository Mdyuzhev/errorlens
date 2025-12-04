"""ErrorLens API - FastAPI entrypoint."""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

from app.analyzer import analyze_errors
from app.config import settings
from app.database import async_session_maker, init_db
from app.middleware.jwt_auth import require_auth
from app.middleware.rate_limit import rate_limit_middleware
from app.models.user import User
from app.models_pydantic import (
    AnalyzeRequest,
    AnalyzeResponse,
    DetectedVariable,
    ExportPostmanRequest,
    ExportPostmanResponse,
    ExportPytestRequest,
    ExportRestAssuredRequest,
    ExportK6Request,
    ExportTestItRequest,
    GenerateTicketRequest,
    GenerateTicketResponse,
    RecordedHttpExchange,
    RequestAssertion,
    RunTestRequest,
    SessionAnalysisRequest,
    SessionAnalysisResponse,
    TestRunStatus,
)
from app.generators import (
    generate_postman_collection,
    generate_pytest_file,
    generate_pytest_file_async,
    generate_restassured_file,
    generate_pom_xml,
    generate_k6_file,
    generate_testit_testcase,
)
from app.ticket_generator import generate_smart_ticket
from app.test_runner import run_pytest, run_restassured, get_test_run, create_test_run
from app.routers import auth, sessions, testcases, tasks, articles, testruns
from app.integrations.testit_client import testit_client, TestItTestCase, TestItStep
from app.services.auth import init_admin_user
from app.session_analyzer import analyze_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Create admin user if not exists
    async with async_session_maker() as db:
        await init_admin_user(db)

    yield
    # Shutdown: cleanup if needed
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
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(testcases.router)
app.include_router(tasks.router)
app.include_router(articles.router)
app.include_router(testruns.router)

# Static dashboard serving for Railway
# Path varies: in Docker container it's /app/dashboard-vue/dist
# Locally it's relative to backend/app/main.py
DASHBOARD_PATH = None
for p in [
    Path("/app/dashboard-vue/dist"),  # Railway Docker container
    Path(__file__).parent.parent.parent / "dashboard-vue" / "dist",  # Local dev
    Path(__file__).parent.parent.parent / "dashboard",  # Legacy fallback
]:
    if p.exists() and (p / "index.html").exists():
        DASHBOARD_PATH = p
        # Mount static assets
        if (p / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(p / "assets")), name="assets")
        logger.info(f"Serving dashboard from {p}")
        break

if not DASHBOARD_PATH:
    logger.warning("No dashboard found, serving API only")

# Serve bookmarklet script
BOOKMARKLET_PATH = None
for p in [
    Path("/app/bookmarklet"),  # Railway Docker container
    Path(__file__).parent.parent.parent / "bookmarklet",  # Local dev
]:
    if p.exists() and (p / "recorder.js").exists():
        BOOKMARKLET_PATH = p
        app.mount("/bookmarklet", StaticFiles(directory=str(p)), name="bookmarklet")
        logger.info(f"Serving bookmarklet from {p}")
        break

if not BOOKMARKLET_PATH:
    logger.warning("No bookmarklet found")


# Root route to serve SPA - MUST be defined before catch-all routes
# Use hash router in Vue (/#/) so all navigation is client-side
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


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    http_request: Request,
    response: Response,
    remaining: int = Depends(rate_limit_middleware),
    _: User = Depends(require_auth),
) -> AnalyzeResponse:
    """
    Analyze captured browser errors using AI.

    Accepts console logs, network errors, and JS exceptions,
    returns structured analysis with probable cause and fix suggestions.
    """
    # Add rate limit header
    if remaining >= 0:
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_day)

    # Validate payload limits
    if len(request.console_logs) > settings.max_console_logs:
        raise HTTPException(
            status_code=400,
            detail=f"Превышен лимит console_logs: максимум {settings.max_console_logs}",
        )
    if len(request.network_errors) > settings.max_network_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Превышен лимит network_errors: максимум {settings.max_network_errors}",
        )

    total_events = (
        len(request.console_logs)
        + len(request.js_exceptions)
        + len(request.network_errors)
    )

    if total_events == 0:
        raise HTTPException(
            status_code=400,
            detail="No error data to analyze. Provide console_logs, js_exceptions, or network_errors.",
        )

    logger.info(f"Analyzing {total_events} events from {request.url}")

    try:
        result = await analyze_errors(request)
        logger.info(f"Analysis complete: severity={result.severity}")
        return result
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.post("/export/postman", response_model=ExportPostmanResponse)
async def export_postman(
    request: ExportPostmanRequest,
    _: User = Depends(require_auth),
) -> ExportPostmanResponse:
    """
    Generate Postman Collection from recorded HTTP exchanges.

    Converts recorded requests/responses into a Postman Collection v2.1
    with optional test assertions and environment variables.
    """
    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to export.",
        )

    logger.info(f"Generating Postman collection from {len(request.recorded_requests)} requests")

    try:
        result = generate_postman_collection(request)
        logger.info(f"Generated collection with {result.requests_count} items")
        return result
    except Exception as e:
        logger.exception(f"Postman export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@app.post("/export/pytest")
async def export_pytest(
    request: ExportPytestRequest,
    _: User = Depends(require_auth),
) -> Response:
    """
    Generate pytest file from recorded HTTP exchanges.

    Converts recorded requests/responses into a runnable pytest file
    with assertions based on recorded responses.

    Features:
    - Auto-detects auth endpoints and extracts tokens
    - Shares tokens between tests via class variable
    - LLM-generated comments explaining business logic (optional)
    - Beautiful test summary with pass/fail statistics
    """
    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to export.",
        )

    logger.info(
        f"Generating pytest file from {len(request.recorded_requests)} requests "
        f"(use_llm={request.use_llm})"
    )

    try:
        if request.use_llm:
            # Use async version with LLM comments
            content = await generate_pytest_file_async(
                recorded_requests=request.recorded_requests,
                test_name=request.test_name,
                base_url_variable=request.base_url_variable,
                use_llm=True,
            )
        else:
            # Sync version without LLM
            content = generate_pytest_file(
                recorded_requests=request.recorded_requests,
                test_name=request.test_name,
                base_url_variable=request.base_url_variable,
            )

        logger.info(f"Generated pytest file with {len(request.recorded_requests)} tests")

        return Response(
            content=content,
            media_type="text/x-python",
            headers={
                "Content-Disposition": f'attachment; filename="{request.test_name}.py"'
            },
        )
    except Exception as e:
        logger.exception(f"Pytest export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@app.post("/analyze/session", response_model=SessionAnalysisResponse)
async def analyze_session_endpoint(
    request: SessionAnalysisRequest,
    _: User = Depends(require_auth),
) -> SessionAnalysisResponse:
    """
    Analyze recorded session for test generation.

    Detects variables (tokens, IDs), groups requests by scenario,
    and extracts assertions for each request.
    """
    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to analyze.",
        )

    logger.info(f"Analyzing session with {len(request.recorded_requests)} requests")

    try:
        result = analyze_session(request.recorded_requests)

        # Convert to response model
        variables = {
            name: DetectedVariable(
                name=name,
                source_request_id=data["source_request_id"],
                source_path=data["source_path"],
                value=data["value"][:50] + "..." if len(data["value"]) > 50 else data["value"],
                used_in=data["used_in"],
            )
            for name, data in result["variables"].items()
        }

        assertions = {
            req_id: [
                RequestAssertion(
                    type=a["type"],
                    path=a.get("path"),
                    expected=str(a["expected"]),
                    description=a["description"],
                )
                for a in assertion_list
            ]
            for req_id, assertion_list in result["assertions"].items()
        }

        logger.info(f"Analysis complete: {result['summary']}")

        return SessionAnalysisResponse(
            variables=variables,
            groups=result["groups"],
            assertions=assertions,
            summary=result["summary"],
        )
    except Exception as e:
        logger.exception(f"Session analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.post("/tickets/generate", response_model=GenerateTicketResponse)
async def create_ticket(
    request: GenerateTicketRequest,
    db=Depends(sessions.get_db),
    _: User = Depends(require_auth),
) -> GenerateTicketResponse:
    """
    Generate bug ticket from session analysis.

    Supports Jira, GitHub Issue, and plain Markdown formats.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.db_models import Session

    # Get session with analysis and data
    query = (
        select(Session)
        .options(selectinload(Session.analysis), selectinload(Session.data))
        .where(Session.id == request.session_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.analysis:
        raise HTTPException(status_code=400, detail="Session has no analysis")

    analysis_dict = {
        "summary": session.analysis.summary,
        "probable_cause": session.analysis.probable_cause,
        "suggested_fix": session.analysis.suggested_fix,
        "severity": session.analysis.severity,
        "details": session.analysis.details,
    }

    # Get data from session.data relationship
    session_data = session.data

    # Use smart ticket generator with full session data
    ticket = generate_smart_ticket(
        analysis=analysis_dict,
        url=session.url,
        user_agent=session.user_agent,
        recorded_requests=session_data.recorded_requests if session_data else [],
        console_logs=session_data.console_logs if session_data else [],
        js_exceptions=session_data.js_exceptions if session_data else [],
        additional_info=request.additional_info,
        format=request.format,
    )

    logger.info(f"Generated {request.format} ticket for session {request.session_id}")

    return GenerateTicketResponse(**ticket)


@app.post("/tests/run")
async def start_test_run(
    request: RunTestRequest,
    db=Depends(sessions.get_db),
    _: User = Depends(require_auth),
) -> dict:
    """
    Start pytest execution.

    Provide either session_id to generate tests from recorded requests,
    or test_code to run custom test code.
    """
    import asyncio

    test_id = create_test_run()

    if request.session_id:
        # Get test code from session
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.db_models import Session

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

        # Generate test code
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

    # Run in background
    asyncio.create_task(run_pytest(test_code, test_id))

    logger.info(f"Started test run {test_id}")

    return {"test_id": test_id, "status": "started"}


@app.post("/tests/run/restassured")
async def start_restassured_test_run(
    request: RunTestRequest,
    db=Depends(sessions.get_db),
    _: User = Depends(require_auth),
) -> dict:
    """
    Start REST Assured (Java/Maven) test execution.
    """
    import asyncio

    test_id = create_test_run()

    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Get session data
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.db_models import Session

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

    # Generate Java code
    recorded = []
    for req_dict in session.data.recorded_requests:
        if isinstance(req_dict, dict):
            recorded.append(RecordedHttpExchange(**req_dict))
        else:
            recorded.append(req_dict)

    java_code = generate_restassured_file(recorded)
    pom_xml = generate_pom_xml()

    # Run in background
    asyncio.create_task(run_restassured(java_code, pom_xml, test_id))

    logger.info(f"Started REST Assured test run {test_id}")

    return {"test_id": test_id, "status": "started"}


@app.get("/tests/{test_id}/status")
async def get_test_status(
    test_id: str,
    _: User = Depends(require_auth),
) -> dict:
    """Get test run status and output."""
    result = get_test_run(test_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test run not found")
    return result


@app.post("/export/restassured")
async def export_restassured(
    request: ExportRestAssuredRequest,
    _: User = Depends(require_auth),
):
    """
    Generate REST Assured test file (Java).

    Returns a ZIP with Java test file and Maven pom.xml if include_pom=True,
    otherwise returns just the Java file.
    """
    import io
    import zipfile

    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to export.",
        )

    logger.info(f"Generating REST Assured tests from {len(request.recorded_requests)} requests")

    try:
        java_code = generate_restassured_file(
            recorded_requests=request.recorded_requests,
            class_name=request.class_name,
            package_name=request.package_name
        )

        if request.include_pom:
            # Return ZIP with Java file + pom.xml
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Create package directory structure
                package_path = request.package_name.replace('.', '/')
                zf.writestr(
                    f"src/test/java/{package_path}/{request.class_name}.java",
                    java_code
                )
                zf.writestr("pom.xml", generate_pom_xml())
                zf.writestr("README.md", f"""# ErrorLens Generated Tests

## Run tests

```bash
mvn test
```

## Requirements

- Java 17+
- Maven 3.6+
""")

            zip_buffer.seek(0)
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{request.class_name}.zip"'
                }
            )
        else:
            return Response(
                content=java_code,
                media_type="text/x-java",
                headers={
                    "Content-Disposition": f'attachment; filename="{request.class_name}.java"'
                }
            )

    except Exception as e:
        logger.exception(f"REST Assured export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@app.post("/export/k6")
async def export_k6(
    request: ExportK6Request,
    _: User = Depends(require_auth),
):
    """
    Generate k6 load test script.

    Returns a JavaScript file that can be run with k6.
    """
    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to export.",
        )

    logger.info(f"Generating k6 load test from {len(request.recorded_requests)} requests")

    try:
        js_code = generate_k6_file(
            recorded_requests=request.recorded_requests,
            vus=request.vus,
            duration=request.duration,
        )

        return Response(
            content=js_code,
            media_type="text/javascript",
            headers={
                "Content-Disposition": 'attachment; filename="load_test.js"'
            }
        )

    except Exception as e:
        logger.exception(f"k6 export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@app.post("/export/testit")
async def export_testit(
    request: ExportTestItRequest,
    format: str = "json",
    _: User = Depends(require_auth),
):
    """
    Generate TestIt test case from recorded requests.

    Args:
        format: json, xml, or markdown
    """
    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to export.",
        )

    logger.info(f"Generating TestIt test case from {len(request.recorded_requests)} requests")

    try:
        session_data = {
            "id": "export",
            "url": request.recorded_requests[0].request.url if request.recorded_requests else "",
            "recorded_requests": [r.model_dump() for r in request.recorded_requests],
            "has_errors": any(
                r.response.status >= 400
                for r in request.recorded_requests
                if r.response
            ),
        }

        analysis = request.analysis.model_dump() if request.analysis else None

        content = generate_testit_testcase(session_data, analysis, format)

        # Determine content type and filename
        if format == "xml":
            media_type = "application/xml"
            filename = "testcase.xml"
        elif format == "markdown":
            media_type = "text/markdown"
            filename = "testcase.md"
        else:
            media_type = "application/json"
            filename = "testcase.json"

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.exception(f"TestIt export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


# ============================================================================
# TestIt Integration Endpoints
# ============================================================================


@app.get("/integrations/testit/status")
async def testit_status(_: User = Depends(require_auth)):
    """Check TestIt connection status."""
    if not settings.testit_enabled:
        return {"enabled": False}

    status = await testit_client.check_connection()
    return {"enabled": True, **status}


@app.post("/sessions/{session_id}/send-to-testit")
async def send_session_to_testit(
    session_id: str,
    db=Depends(sessions.get_db),
    _: User = Depends(require_auth),
):
    """
    Send session directly to TestIt as a test case.

    Returns URL to created test case in TestIt.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.db_models import Session
    from app.generators.testit import TestItGenerator

    if not settings.testit_enabled:
        raise HTTPException(status_code=400, detail="TestIt integration is disabled")

    # Get session
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.data), selectinload(Session.analysis))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build session data for generator
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

    # Generate test case
    generator = TestItGenerator(session_data, analysis)
    tc = generator.generate()

    # Convert to TestIt model
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

    # Send to TestIt
    result = await testit_client.create_test_case(test_case)

    if result.get("success"):
        # Save TestIt URL to session
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
