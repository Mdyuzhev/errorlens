"""
Project, Folder, ProjectMember Pydantic Schemas
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ProjectPlan(StrEnum):
    FREE = "free"
    PRO = "pro"


class MemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# === Project Schemas ===


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    key: str | None = None
    prefix: str | None = None

    @model_validator(mode='before')
    @classmethod
    def resolve_prefix(cls, data):
        if isinstance(data, dict):
            if data.get('prefix') and not data.get('key'):
                data['key'] = data['prefix']
        return data


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    plan: ProjectPlan
    owner_id: str
    key: str | None = None
    entity_counter: int = 0
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ProjectWithStats(ProjectResponse):
    members_count: int = 0
    folders_count: int = 0
    sessions_count: int = 0


# === Folder Schemas ===


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: str | None = None


class FolderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    parent_id: str | None = None


class FolderResponse(BaseModel):
    id: str
    name: str
    project_id: str
    parent_id: str | None
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


# === Member Schemas ===


class MemberAdd(BaseModel):
    username: str
    role: MemberRole = MemberRole.MEMBER


class MemberUpdate(BaseModel):
    role: MemberRole


class MemberResponse(BaseModel):
    id: str
    user_id: str
    username: str
    role: MemberRole
    added_at: datetime

    class Config:
        from_attributes = True


# === Limits ===


class PlanLimits(BaseModel):
    max_projects: int
    max_folders_per_project: int
    max_sessions_total: int
    max_members_per_project: int
    max_ai_analyses_per_day: int
    retention_days: int
    max_integrations: int


FREE_LIMITS = PlanLimits(
    max_projects=10,
    max_folders_per_project=10,
    max_sessions_total=100,
    max_members_per_project=3,
    max_ai_analyses_per_day=20,
    retention_days=7,
    max_integrations=1,
)

PRO_LIMITS = PlanLimits(
    max_projects=999999,
    max_folders_per_project=999999,
    max_sessions_total=999999,
    max_members_per_project=999999,
    max_ai_analyses_per_day=999999,
    retention_days=90,
    max_integrations=999999,
)


def get_plan_limits(plan: ProjectPlan) -> PlanLimits:
    return PRO_LIMITS if plan == ProjectPlan.PRO else FREE_LIMITS
