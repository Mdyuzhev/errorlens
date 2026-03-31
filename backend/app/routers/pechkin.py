"""Pechkin (HTTP client) router — collections, requests, proxy, scripts."""

import json
import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.repositories.pechkin_repo import PechkinRepository
from app.routers.pechkin_schemas import (
    CollectionCreate,
    CollectionUpdate,
    ExecuteRequest,
    FolderCreate,
    FolderUpdate,
    RequestCreate,
    RequestUpdate,
    RunCollectionRequest,
    ScriptRequest,
    VariableUpsert,
    collection_to_dict,
    folder_to_dict,
    history_to_dict,
    request_to_dict,
    variable_to_dict,
)
from app.services.pechkin_service import PechkinService
from app.services.postman_importer import import_postman_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pechkin", tags=["pechkin"])


# ── Collections ──────────────────────────────────────────────────


@router.get("/collections")
async def list_collections(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    cols = await repo.list_collections(project_id)
    return [collection_to_dict(c) for c in cols]


@router.post("/collections", status_code=201)
async def create_collection(
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    col = await repo.create_collection(
        project_id=data.project_id, owner_id=user.id,
        name=data.name, description=data.description,
    )
    await db.commit()
    return {
        "id": col.id, "name": col.name, "project_id": col.project_id,
        "owner_id": col.owner_id, "description": col.description,
        "sort_order": col.sort_order,
        "folders": [], "requests": [], "variables": [],
    }


@router.put("/collections/{collection_id}")
async def update_collection(
    collection_id: str,
    data: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    col = await repo.update_collection(
        collection_id, **data.model_dump(exclude_none=True),
    )
    if not col:
        raise HTTPException(404, "Collection not found")
    return collection_to_dict(col)


@router.delete("/collections/{collection_id}", status_code=200)
async def delete_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    ok = await repo.delete_collection(collection_id)
    if not ok:
        raise HTTPException(404, "Collection not found")
    await db.commit()
    return {"ok": True}


# ── Folders ──────────────────────────────────────────────────────


@router.post("/collections/{col_id}/folders", status_code=201)
async def create_folder(
    col_id: str,
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    try:
        folder = await repo.create_folder(
            collection_id=col_id, name=data.name, parent_id=data.parent_id,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"id": folder.id, "name": folder.name}


@router.put("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    data: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    folder = await repo.update_folder(folder_id, **data.model_dump(exclude_none=True))
    if not folder:
        raise HTTPException(404, "Folder not found")
    return folder_to_dict(folder)


@router.delete("/folders/{folder_id}", status_code=200)
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    ok = await repo.delete_folder(folder_id)
    if not ok:
        raise HTTPException(404, "Folder not found")
    await db.commit()
    return {"ok": True}


# ── Requests ─────────────────────────────────────────────────────


@router.get("/collections/{col_id}/requests")
async def list_requests(
    col_id: str,
    folder_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    reqs = await repo.list_requests(col_id, folder_id)
    return [request_to_dict(r) for r in reqs]


@router.post("/collections/{col_id}/requests", status_code=201)
async def create_request(
    col_id: str,
    data: RequestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    req = await repo.create_request(
        collection_id=col_id,
        folder_id=data.folder_id,
        name=data.name,
        method=data.method,
        url=data.url,
        headers=data.headers,
        body=data.body,
        body_type=data.body_type,
        auth=data.auth,
        pre_request_script=data.pre_request_script,
        test_script=data.test_script,
        test_snippets=data.test_snippets,
        extract_variables=data.extract_variables,
        settings=data.settings,
    )
    await db.commit()
    return request_to_dict(req)


@router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    req = await repo.get_request(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    result = request_to_dict(req)
    result["history"] = [history_to_dict(h) for h in (req.history or [])]
    return result


@router.put("/requests/{request_id}")
async def update_request(
    request_id: str,
    data: RequestUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    req = await repo.update_request(request_id, **data.model_dump(exclude_none=True))
    if not req:
        raise HTTPException(404, "Request not found")
    return request_to_dict(req)


@router.delete("/requests/{request_id}", status_code=200)
async def delete_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    ok = await repo.delete_request(request_id)
    if not ok:
        raise HTTPException(404, "Request not found")
    await db.commit()
    return {"ok": True}


# ── Variables ────────────────────────────────────────────────────


@router.get("/collections/{col_id}/variables")
async def list_variables(
    col_id: str,
    scope: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    vars_ = await repo.list_variables(col_id, scope)
    return [variable_to_dict(v) for v in vars_]


@router.put("/collections/{col_id}/variables")
async def upsert_variable(
    col_id: str,
    data: VariableUpsert,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    var = await repo.upsert_variable(
        collection_id=col_id, scope=data.scope,
        name=data.name, value=data.value,
        is_secret=data.is_secret, is_enabled=data.is_enabled,
    )
    await db.commit()
    return variable_to_dict(var)


@router.delete("/variables/{variable_id}", status_code=200)
async def delete_variable(
    variable_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    ok = await repo.delete_variable(variable_id)
    if not ok:
        raise HTTPException(404, "Variable not found")
    await db.commit()
    return {"ok": True}


# ── History ──────────────────────────────────────────────────────


@router.get("/requests/{request_id}/history")
async def list_history(
    request_id: str,
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    entries = await repo.list_history(request_id, limit)
    return [history_to_dict(h) for h in entries]


@router.delete("/requests/{request_id}/history", status_code=200)
async def clear_history(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    count = await repo.clear_history(request_id)
    await db.commit()
    return {"ok": True, "deleted": count}


@router.get("/history")
async def list_recent_history(
    project_id: str = Query(...),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = PechkinRepository(db)
    entries = await repo.list_recent_history(project_id, limit)
    return [history_to_dict(h) for h in entries]


# ── Execute ──────────────────────────────────────────────────────


@router.post("/execute")
async def execute(
    data: ExecuteRequest,
    request_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    svc = PechkinService(db)

    # 1. Run pre-request script (modifies request context if needed)
    modified_headers = dict(data.headers)
    modified_body = data.body
    if data.pre_request_script and data.pre_request_script.strip():
        pre_result = await svc.run_pre_request(
            data.pre_request_script,
            {
                "method": data.method,
                "url": data.url,
                "headers": dict(data.headers),
                "body": data.body,
            },
        )
        # Apply modifications from pre-request script
        if pre_result.get("modified_request"):
            mr = pre_result["modified_request"]
            if mr.get("headers"):
                modified_headers.update(mr["headers"])
            if mr.get("body") is not None:
                modified_body = mr["body"]

    # 2. Execute HTTP request
    resp = await svc.execute_request(
        method=data.method,
        url=data.url,
        headers=modified_headers,
        body=modified_body,
        body_type=data.body_type,
        auth=data.auth,
        variables=data.variables,
        timeout=data.timeout,
        request_id=request_id,
        settings=data.settings,
    )

    result = asdict(resp)

    # 3. Run test script if provided
    if data.test_script and data.test_script.strip():
        try:
            test_result = await svc.run_test_script(
                data.test_script,
                {
                    "method": data.method,
                    "url": data.url,
                    "headers": modified_headers,
                    "body": data.body,
                },
                {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.body,
                    "duration_ms": resp.duration_ms,
                },
            )
            # Attach results: list of {name, passed} dicts
            result["test_results"] = test_result.get("assertions", {}).get("tests", [])
            result["test_output"] = test_result.get("output", [])
            result["test_error"] = test_result.get("error")
        except Exception as e:
            result["test_results"] = [{"name": f"Script error: {str(e)}", "passed": False}]
            result["test_output"] = []
            result["test_error"] = str(e)
    else:
        result["test_results"] = []
        result["test_output"] = []
        result["test_error"] = None

    return result


@router.post("/execute/pre-request")
async def execute_pre_request(
    data: ScriptRequest,
    _: User = Depends(require_auth),
):
    svc = PechkinService.__new__(PechkinService)
    return await svc.run_pre_request(data.code, data.context)


@router.post("/execute/test")
async def execute_test(
    data: ScriptRequest,
    _: User = Depends(require_auth),
):
    svc = PechkinService.__new__(PechkinService)
    context = data.context
    return await svc.run_test_script(
        data.code,
        context.get("request", {}),
        context.get("response", {}),
    )


# ── Collection runner ────────────────────────────────────────────


@router.post("/run-collection")
async def run_collection(
    data: RunCollectionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    svc = PechkinService(db)
    results = await svc.run_collection(
        collection_id=data.collection_id,
        request_ids=data.request_ids,
        delay_ms=data.delay_ms,
        stop_on_error=data.stop_on_error,
        iterations=data.iterations,
        variables=data.variables,
    )
    return {"results": results, "total": len(results)}


# ── Import (stub) ───────────────────────────────────────────────


@router.post("/collections/{col_id}/import")
async def import_postman_endpoint(
    col_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Import Postman Collection v2.1 JSON into existing collection."""
    try:
        content = await file.read()
        json_data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(400, f"Invalid JSON file: {exc}")

    result = import_postman_collection(json_data)
    repo = PechkinRepository(db)

    # Map imported folder IDs to real DB folder IDs
    folder_map: dict[str, str] = {}
    for f in result.folders:
        parent_id = folder_map.get(f.parent_id) if f.parent_id else None
        folder = await repo.create_folder(
            collection_id=col_id, name=f.name, parent_id=parent_id,
        )
        folder_map[f.id] = folder.id

    for r in result.requests:
        folder_id = folder_map.get(r.folder_id) if r.folder_id else None
        await repo.create_request(
            collection_id=col_id, folder_id=folder_id,
            name=r.name, method=r.method, url=r.url,
            headers=r.headers, body=r.body, body_type=r.body_type,
            auth=r.auth, pre_request_script=r.pre_request_script,
            test_script=r.test_script,
        )

    await db.commit()
    return {
        "collection_name": result.collection_name,
        "imported_folders": len(result.folders),
        "imported_requests": len(result.requests),
    }


# ── Export ──────────────────────────────────────────────────────


@router.get("/collections/{col_id}/export")
async def export_collection(
    col_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Export collection as Postman Collection v2.1 JSON."""
    from fastapi.responses import Response
    from app.services.postman_exporter import export_to_postman

    repo = PechkinRepository(db)
    col = await repo.get_collection(col_id)
    if not col:
        raise HTTPException(404, "Collection not found")

    col_dict = collection_to_dict(col)
    postman_json = export_to_postman(col_dict)

    content = json.dumps(postman_json, ensure_ascii=False, indent=2)

    safe_name = col.name.replace(" ", "_").replace("/", "_")[:50]
    filename = f"{safe_name}.postman_collection.json"

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/json; charset=utf-8",
        },
    )
