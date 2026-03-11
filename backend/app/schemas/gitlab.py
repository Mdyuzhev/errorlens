"""Pydantic schemas for GitLab integration API."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateConnectionRequest(BaseModel):
    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)
    verify_ssl: bool = True


class UpdateConnectionRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    token: str | None = None
    verify_ssl: bool | None = None
    is_active: bool | None = None


class ConnectionResponse(BaseModel):
    id: str
    name: str
    url: str
    verify_ssl: bool
    is_active: bool
    token_masked: str
    last_checked_at: datetime | None = None
    last_check_ok: bool | None = None

    model_config = {"from_attributes": True}


class CheckResponse(BaseModel):
    ok: bool
    username: str | None = None
    error: str | None = None


class GitLabProjectResponse(BaseModel):
    id: int
    name: str
    path_with_namespace: str
    web_url: str
    default_branch: str


class GitLabPipelineResponse(BaseModel):
    id: int
    status: str
    ref: str
    created_at: str
    web_url: str
