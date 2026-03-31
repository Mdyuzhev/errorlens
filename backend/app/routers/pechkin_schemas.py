"""Pechkin Pydantic schemas and serialization helpers."""

from pydantic import BaseModel, model_validator


# ── Pydantic schemas ────────────────────────────────────────────


class CollectionCreate(BaseModel):
    project_id: str
    name: str
    description: str | None = None


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class FolderCreate(BaseModel):
    name: str
    parent_id: str | None = None


class FolderUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None


class RequestCreate(BaseModel):
    name: str
    method: str = "GET"
    url: str = ""
    folder_id: str | None = None
    headers: dict = {}
    body: str | None = None
    body_type: str = "none"
    auth: dict = {}
    pre_request_script: str | None = None
    test_script: str | None = None
    test_snippets: list = []
    extract_variables: list = []


class RequestUpdate(BaseModel):
    name: str | None = None
    method: str | None = None
    url: str | None = None
    folder_id: str | None = None
    headers: dict | None = None
    body: str | None = None
    body_type: str | None = None
    auth: dict | None = None
    pre_request_script: str | None = None
    test_script: str | None = None
    test_snippets: list | None = None
    extract_variables: list | None = None
    sort_order: int | None = None


class VariableUpsert(BaseModel):
    scope: str
    name: str
    value: str
    is_secret: bool = False
    is_enabled: bool = True


class ExecuteRequest(BaseModel):
    method: str
    url: str
    headers: dict = {}
    body: str | None = None
    body_type: str = "none"
    auth: dict = {}
    variables: dict = {}
    timeout: int = 30
    pre_request_script: str | None = None
    test_script: str | None = None


class ScriptRequest(BaseModel):
    code: str
    context: dict = {}


class RunCollectionRequest(BaseModel):
    collection_id: str
    request_ids: list[str] | None = None
    delay_ms: int | None = 0
    stop_on_error: bool = False
    iterations: int | None = 1
    variables: dict = {}

    @model_validator(mode="before")
    @classmethod
    def coerce_nulls(cls, values):
        if isinstance(values, dict):
            if values.get("delay_ms") is None:
                values["delay_ms"] = 0
            if values.get("iterations") is None:
                values["iterations"] = 1
        return values


# ── Serialization helpers ────────────────────────────────────────


def collection_to_dict(col) -> dict:
    return {
        "id": col.id,
        "project_id": col.project_id,
        "owner_id": col.owner_id,
        "name": col.name,
        "description": col.description,
        "sort_order": col.sort_order,
        "created_at": col.created_at.isoformat() if col.created_at else None,
        "updated_at": col.updated_at.isoformat() if col.updated_at else None,
        "folders": [folder_to_dict(f) for f in (col.folders or [])],
        "requests": [request_to_dict(r) for r in (col.requests or [])],
        "variables": [variable_to_dict(v) for v in (col.variables or [])],
    }


def folder_to_dict(f) -> dict:
    return {
        "id": f.id,
        "collection_id": f.collection_id,
        "parent_id": f.parent_id,
        "name": f.name,
        "sort_order": f.sort_order,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "children": [folder_to_dict(c) for c in (f.children or [])],
        "requests": [request_to_dict(r) for r in (f.requests or [])],
    }


def request_to_dict(r) -> dict:
    return {
        "id": r.id,
        "collection_id": r.collection_id,
        "folder_id": r.folder_id,
        "name": r.name,
        "method": r.method,
        "url": r.url,
        "headers": r.headers,
        "body": r.body,
        "body_type": r.body_type,
        "auth": r.auth,
        "pre_request_script": r.pre_request_script,
        "test_script": r.test_script,
        "test_snippets": r.test_snippets,
        "extract_variables": r.extract_variables,
        "sort_order": r.sort_order,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def variable_to_dict(v) -> dict:
    return {
        "id": v.id,
        "collection_id": v.collection_id,
        "scope": v.scope,
        "name": v.name,
        "value": "***" if v.is_secret else v.value,
        "is_secret": v.is_secret,
        "is_enabled": v.is_enabled,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


def history_to_dict(h) -> dict:
    return {
        "id": h.id,
        "request_id": h.request_id,
        "resolved_url": h.resolved_url,
        "method": h.method,
        "request_headers": h.request_headers,
        "request_body": h.request_body,
        "status_code": h.status_code,
        "response_headers": h.response_headers,
        "response_body": h.response_body,
        "duration_ms": h.duration_ms,
        "size_bytes": h.size_bytes,
        "error": h.error,
        "executed_at": h.executed_at.isoformat() if h.executed_at else None,
    }
