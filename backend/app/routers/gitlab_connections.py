"""GitLab Connections API router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.repositories.gitlab_connection_repo import GitLabConnectionRepository
from app.schemas.gitlab import (
    CheckResponse,
    ConnectionResponse,
    CreateConnectionRequest,
    GitLabPipelineResponse,
    GitLabProjectResponse,
    UpdateConnectionRequest,
)
from app.services.exceptions import GitLabAuthError, GitLabConnectionError
from app.services.gitlab_service import GitLabService
from app.utils.crypto import encrypt_token, mask_token

router = APIRouter(prefix="/v1/gitlab", tags=["gitlab"])

gitlab_svc = GitLabService()


def _to_response(conn) -> ConnectionResponse:
    """Convert model to response with masked token."""
    from app.utils.crypto import decrypt_token

    try:
        plain = decrypt_token(conn.token_encrypted)
        masked = mask_token(plain)
    except Exception:
        masked = "****"

    return ConnectionResponse(
        id=conn.id,
        name=conn.name,
        url=conn.url,
        verify_ssl=conn.verify_ssl,
        is_active=conn.is_active,
        token_masked=masked,
        last_checked_at=conn.last_checked_at,
        last_check_ok=conn.last_check_ok,
    )


# --- Connections CRUD ---


@router.get("/connections", response_model=list[ConnectionResponse])
async def list_connections(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List GitLab connections for a project."""
    repo = GitLabConnectionRepository(db)
    connections = await repo.get_by_org(project_id, active_only=False)
    return [_to_response(c) for c in connections]


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    data: CreateConnectionRequest,
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new GitLab connection."""
    repo = GitLabConnectionRepository(db)
    conn = await repo.create({
        "organization_id": project_id,
        "name": data.name,
        "url": data.url.rstrip("/"),
        "token_encrypted": encrypt_token(data.token),
        "verify_ssl": data.verify_ssl,
        "created_by": user.id,
    })
    return _to_response(conn)


@router.put("/connections/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: str,
    data: UpdateConnectionRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update a GitLab connection."""
    repo = GitLabConnectionRepository(db)
    conn = await repo.get_by_id(connection_id)
    if not conn:
        raise HTTPException(404, "Connection not found")

    update_data: dict = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.url is not None:
        update_data["url"] = data.url.rstrip("/")
    if data.token is not None:
        update_data["token_encrypted"] = encrypt_token(data.token)
    if data.verify_ssl is not None:
        update_data["verify_ssl"] = data.verify_ssl
    if data.is_active is not None:
        update_data["is_active"] = data.is_active

    updated = await repo.update(connection_id, update_data)
    return _to_response(updated)


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete a GitLab connection."""
    repo = GitLabConnectionRepository(db)
    deleted = await repo.delete(connection_id)
    if not deleted:
        raise HTTPException(404, "Connection not found")


@router.post("/connections/{connection_id}/check", response_model=CheckResponse)
async def check_connection(
    connection_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Test a GitLab connection."""
    repo = GitLabConnectionRepository(db)
    conn = await repo.get_by_id(connection_id)
    if not conn:
        raise HTTPException(404, "Connection not found")

    result = await gitlab_svc.check_connection(conn)
    await repo.update_check_status(connection_id, result["ok"])
    return CheckResponse(**result)


# --- GitLab Proxy Endpoints ---


@router.get(
    "/connections/{connection_id}/projects",
    response_model=list[GitLabProjectResponse],
)
async def list_gitlab_projects(
    connection_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List projects from a GitLab connection."""
    repo = GitLabConnectionRepository(db)
    conn = await repo.get_by_id(connection_id)
    if not conn:
        raise HTTPException(404, "Connection not found")

    try:
        projects = await gitlab_svc.get_projects(conn)
    except GitLabAuthError:
        raise HTTPException(401, {"error": "auth_failed"})
    except GitLabConnectionError as exc:
        raise HTTPException(502, {"error": "connection_failed", "message": str(exc)})

    return [GitLabProjectResponse(**p) for p in projects]


@router.get(
    "/connections/{connection_id}/projects/{project_id}/pipelines",
    response_model=list[GitLabPipelineResponse],
)
async def list_pipelines(
    connection_id: str,
    project_id: int,
    ref: str | None = None,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List pipelines for a GitLab project."""
    repo = GitLabConnectionRepository(db)
    conn = await repo.get_by_id(connection_id)
    if not conn:
        raise HTTPException(404, "Connection not found")

    try:
        pipelines = await gitlab_svc.get_pipelines(conn, project_id, ref)
    except GitLabAuthError:
        raise HTTPException(401, {"error": "auth_failed"})
    except GitLabConnectionError as exc:
        raise HTTPException(502, {"error": "connection_failed", "message": str(exc)})

    return [GitLabPipelineResponse(**p) for p in pipelines]


@router.get(
    "/connections/{connection_id}/projects/{project_id}/branches",
    response_model=list[str],
)
async def list_branches(
    connection_id: str,
    project_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List branches for a GitLab project."""
    repo = GitLabConnectionRepository(db)
    conn = await repo.get_by_id(connection_id)
    if not conn:
        raise HTTPException(404, "Connection not found")

    try:
        branches = await gitlab_svc.get_branches(conn, project_id)
    except GitLabAuthError:
        raise HTTPException(401, {"error": "auth_failed"})
    except GitLabConnectionError as exc:
        raise HTTPException(502, {"error": "connection_failed", "message": str(exc)})

    return branches
