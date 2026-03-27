"""Spec-based test generator API — static OpenAPI → test code."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.spec_gen_service import SpecGenService

router = APIRouter(prefix="/api/v1/generator/spec", tags=["spec-generator"])


# --- Pydantic schemas ---

class SpecParseRequest(BaseModel):
    spec: str | None = None
    spec_url: str | None = None


class EndpointSummary(BaseModel):
    id: str
    method: str
    path: str
    summary: str | None
    tags: list[str]
    params_count: int
    has_request_body: bool
    has_response_schema: bool


class SpecParseResponse(BaseModel):
    title: str
    version: str
    base_url: str
    endpoints: list[EndpointSummary]


class GeneratorConfigRequest(BaseModel):
    framework: str = "pytest"
    base_url: str = ""
    generate_negative_tests: bool = True
    use_placeholders: bool = True


class SpecGenerateRequest(BaseModel):
    spec: str | None = None
    spec_url: str | None = None
    endpoint_ids: list[str] | None = None
    config: GeneratorConfigRequest = GeneratorConfigRequest()


class GeneratedFileResponse(BaseModel):
    filename: str
    content: str
    language: str


class GenerationStatsResponse(BaseModel):
    total_endpoints: int
    total_tests: int
    positive_tests: int
    negative_tests: int
    assertions: int


class SpecGenerateResponse(BaseModel):
    files: list[GeneratedFileResponse]
    stats: GenerationStatsResponse


# --- Endpoints ---

@router.post("/parse", response_model=SpecParseResponse)
async def parse_spec(
    request: SpecParseRequest,
    user: User = Depends(require_auth),
):
    if not request.spec and not request.spec_url:
        raise HTTPException(status_code=400, detail="Provide spec or spec_url")
    service = SpecGenService()
    try:
        return service.parse_spec(request.spec, request.spec_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "Cannot fetch" in str(e):
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to parse spec: {e}")


@router.post("/generate", response_model=SpecGenerateResponse)
async def generate_from_spec(
    request: SpecGenerateRequest,
    user: User = Depends(require_auth),
):
    if not request.spec and not request.spec_url:
        raise HTTPException(status_code=400, detail="Provide spec or spec_url")
    service = SpecGenService()
    try:
        return service.generate_tests(
            spec=request.spec,
            spec_url=request.spec_url,
            endpoint_ids=request.endpoint_ids,
            config=request.config,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "Cannot fetch" in str(e):
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to generate tests: {e}")
