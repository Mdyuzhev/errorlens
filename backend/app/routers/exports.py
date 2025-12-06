"""Export endpoints for various test formats."""

import io
import logging
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.generators import (
    generate_k6_file,
    generate_pom_xml,
    generate_postman_collection,
    generate_pytest_file,
    generate_pytest_file_async,
    generate_restassured_file,
    generate_testit_testcase,
)
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.models_pydantic import (
    ExportK6Request,
    ExportPostmanRequest,
    ExportPostmanResponse,
    ExportPytestRequest,
    ExportRestAssuredRequest,
    ExportTestItRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["exports"])


@router.post("/postman", response_model=ExportPostmanResponse)
async def export_postman(
    request: ExportPostmanRequest,
    _: User = Depends(require_auth),
) -> ExportPostmanResponse:
    """Generate Postman Collection from recorded HTTP exchanges."""
    if not request.recorded_requests:
        raise HTTPException(status_code=400, detail="No recorded requests to export.")

    logger.info(f"Generating Postman collection from {len(request.recorded_requests)} requests")

    try:
        result = generate_postman_collection(request)
        logger.info(f"Generated collection with {result.requests_count} items")
        return result
    except Exception as e:
        logger.exception(f"Postman export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.post("/pytest")
async def export_pytest(
    request: ExportPytestRequest,
    _: User = Depends(require_auth),
) -> Response:
    """Generate pytest file from recorded HTTP exchanges."""
    if not request.recorded_requests:
        raise HTTPException(status_code=400, detail="No recorded requests to export.")

    logger.info(
        f"Generating pytest file from {len(request.recorded_requests)} requests "
        f"(use_llm={request.use_llm})"
    )

    try:
        if request.use_llm:
            content = await generate_pytest_file_async(
                recorded_requests=request.recorded_requests,
                test_name=request.test_name,
                base_url_variable=request.base_url_variable,
                use_llm=True,
            )
        else:
            content = generate_pytest_file(
                recorded_requests=request.recorded_requests,
                test_name=request.test_name,
                base_url_variable=request.base_url_variable,
            )

        logger.info(f"Generated pytest file with {len(request.recorded_requests)} tests")

        return Response(
            content=content,
            media_type="text/x-python",
            headers={"Content-Disposition": f'attachment; filename="{request.test_name}.py"'},
        )
    except Exception as e:
        logger.exception(f"Pytest export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.post("/restassured")
async def export_restassured(
    request: ExportRestAssuredRequest,
    _: User = Depends(require_auth),
):
    """Generate REST Assured test file (Java)."""
    if not request.recorded_requests:
        raise HTTPException(status_code=400, detail="No recorded requests to export.")

    logger.info(f"Generating REST Assured tests from {len(request.recorded_requests)} requests")

    try:
        java_code = generate_restassured_file(
            recorded_requests=request.recorded_requests,
            class_name=request.class_name,
            package_name=request.package_name,
        )

        if request.include_pom:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                package_path = request.package_name.replace(".", "/")
                zf.writestr(f"src/test/java/{package_path}/{request.class_name}.java", java_code)
                zf.writestr("pom.xml", generate_pom_xml())
                zf.writestr("README.md", "# ErrorLens Generated Tests\n\n## Run: mvn test")

            zip_buffer.seek(0)
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{request.class_name}.zip"'},
            )
        else:
            return Response(
                content=java_code,
                media_type="text/x-java",
                headers={
                    "Content-Disposition": f'attachment; filename="{request.class_name}.java"'
                },
            )

    except Exception as e:
        logger.exception(f"REST Assured export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.post("/k6")
async def export_k6(
    request: ExportK6Request,
    _: User = Depends(require_auth),
):
    """Generate k6 load test script."""
    if not request.recorded_requests:
        raise HTTPException(status_code=400, detail="No recorded requests to export.")

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
            headers={"Content-Disposition": 'attachment; filename="load_test.js"'},
        )

    except Exception as e:
        logger.exception(f"k6 export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.post("/testit")
async def export_testit(
    request: ExportTestItRequest,
    format: str = "json",
    _: User = Depends(require_auth),
):
    """Generate TestIt test case from recorded requests."""
    if not request.recorded_requests:
        raise HTTPException(status_code=400, detail="No recorded requests to export.")

    logger.info(f"Generating TestIt test case from {len(request.recorded_requests)} requests")

    try:
        session_data = {
            "id": "export",
            "url": request.recorded_requests[0].request.url if request.recorded_requests else "",
            "recorded_requests": [r.model_dump() for r in request.recorded_requests],
            "has_errors": any(
                r.response.status >= 400 for r in request.recorded_requests if r.response
            ),
        }

        analysis = request.analysis.model_dump() if request.analysis else None
        content = generate_testit_testcase(session_data, analysis, format)

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
