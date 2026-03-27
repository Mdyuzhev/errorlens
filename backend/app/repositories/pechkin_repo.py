"""Pechkin (HTTP client) repository — CRUD for collections, folders, requests, variables, history."""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pechkin import (
    PechkinCollection,
    PechkinFolder,
    PechkinRequest,
    PechkinRequestHistory,
    PechkinVariable,
)


class PechkinRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Collections ──────────────────────────────────────────────

    async def list_collections(self, project_id: str) -> list[PechkinCollection]:
        stmt = (
            select(PechkinCollection)
            .where(PechkinCollection.project_id == project_id)
            .options(
                selectinload(PechkinCollection.folders).selectinload(PechkinFolder.requests),
                selectinload(PechkinCollection.folders).selectinload(PechkinFolder.children),
                selectinload(PechkinCollection.requests),
                selectinload(PechkinCollection.variables),
            )
            .order_by(PechkinCollection.sort_order, PechkinCollection.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_collection(self, collection_id: str) -> PechkinCollection | None:
        stmt = (
            select(PechkinCollection)
            .where(PechkinCollection.id == collection_id)
            .options(
                selectinload(PechkinCollection.folders).selectinload(PechkinFolder.requests),
                selectinload(PechkinCollection.folders).selectinload(PechkinFolder.children),
                selectinload(PechkinCollection.requests),
                selectinload(PechkinCollection.variables),
            )
        )
        result = await self.db.execute(stmt)
        return result.unique().scalars().first()

    async def create_collection(
        self, project_id: str, owner_id: str, name: str, description: str | None = None,
    ) -> PechkinCollection:
        col = PechkinCollection(
            project_id=project_id, owner_id=owner_id,
            name=name, description=description,
        )
        self.db.add(col)
        await self.db.flush()
        await self.db.refresh(col)
        return col

    async def update_collection(self, collection_id: str, **kwargs) -> PechkinCollection | None:
        col = await self.get_collection(collection_id)
        if not col:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(col, k, v)
        col.updated_at = datetime.utcnow()
        await self.db.flush()
        return col

    async def delete_collection(self, collection_id: str) -> bool:
        stmt = delete(PechkinCollection).where(PechkinCollection.id == collection_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    # ── Folders ──────────────────────────────────────────────────

    async def create_folder(
        self, collection_id: str, name: str, parent_id: str | None = None,
    ) -> PechkinFolder:
        folder = PechkinFolder(
            collection_id=collection_id, name=name, parent_id=parent_id,
        )
        self.db.add(folder)
        await self.db.flush()
        await self.db.refresh(folder)
        return folder

    async def update_folder(self, folder_id: str, **kwargs) -> PechkinFolder | None:
        stmt = select(PechkinFolder).where(PechkinFolder.id == folder_id)
        result = await self.db.execute(stmt)
        folder = result.scalars().first()
        if not folder:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(folder, k, v)
        await self.db.flush()
        return folder

    async def delete_folder(self, folder_id: str) -> bool:
        stmt = delete(PechkinFolder).where(PechkinFolder.id == folder_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    # ── Requests ─────────────────────────────────────────────────

    async def list_requests(
        self, collection_id: str, folder_id: str | None = None,
    ) -> list[PechkinRequest]:
        stmt = select(PechkinRequest).where(PechkinRequest.collection_id == collection_id)
        if folder_id is not None:
            stmt = stmt.where(PechkinRequest.folder_id == folder_id)
        else:
            stmt = stmt.where(PechkinRequest.folder_id.is_(None))
        stmt = stmt.order_by(PechkinRequest.sort_order, PechkinRequest.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_all_requests(self, collection_id: str) -> list[PechkinRequest]:
        """All requests in collection regardless of folder."""
        stmt = (
            select(PechkinRequest)
            .where(PechkinRequest.collection_id == collection_id)
            .order_by(PechkinRequest.sort_order, PechkinRequest.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_request(self, request_id: str) -> PechkinRequest | None:
        stmt = (
            select(PechkinRequest)
            .where(PechkinRequest.id == request_id)
            .options(selectinload(PechkinRequest.history))
        )
        result = await self.db.execute(stmt)
        return result.unique().scalars().first()

    async def create_request(
        self, collection_id: str, folder_id: str | None,
        name: str, method: str, url: str, **kwargs,
    ) -> PechkinRequest:
        req = PechkinRequest(
            collection_id=collection_id, folder_id=folder_id,
            name=name, method=method, url=url, **kwargs,
        )
        self.db.add(req)
        await self.db.flush()
        await self.db.refresh(req)
        return req

    async def update_request(self, request_id: str, **kwargs) -> PechkinRequest | None:
        stmt = select(PechkinRequest).where(PechkinRequest.id == request_id)
        result = await self.db.execute(stmt)
        req = result.scalars().first()
        if not req:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(req, k, v)
        req.updated_at = datetime.utcnow()
        await self.db.flush()
        return req

    async def delete_request(self, request_id: str) -> bool:
        stmt = delete(PechkinRequest).where(PechkinRequest.id == request_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    # ── Variables ────────────────────────────────────────────────

    async def list_variables(
        self, collection_id: str, scope: str | None = None,
    ) -> list[PechkinVariable]:
        stmt = select(PechkinVariable).where(PechkinVariable.collection_id == collection_id)
        if scope:
            stmt = stmt.where(PechkinVariable.scope == scope)
        stmt = stmt.order_by(PechkinVariable.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert_variable(
        self, collection_id: str, scope: str, name: str,
        value: str, is_secret: bool = False, is_enabled: bool = True,
    ) -> PechkinVariable:
        stmt = (
            select(PechkinVariable)
            .where(
                PechkinVariable.collection_id == collection_id,
                PechkinVariable.scope == scope,
                PechkinVariable.name == name,
            )
        )
        result = await self.db.execute(stmt)
        var = result.scalars().first()
        if var:
            var.value = value
            var.is_secret = is_secret
            var.is_enabled = is_enabled
        else:
            var = PechkinVariable(
                collection_id=collection_id, scope=scope,
                name=name, value=value,
                is_secret=is_secret, is_enabled=is_enabled,
            )
            self.db.add(var)
        await self.db.flush()
        await self.db.refresh(var)
        return var

    async def delete_variable(self, variable_id: str) -> bool:
        stmt = delete(PechkinVariable).where(PechkinVariable.id == variable_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    # ── History ──────────────────────────────────────────────────

    async def add_history(
        self, request_id: str, resolved_url: str, method: str,
        request_headers: dict, request_body: str | None,
        status_code: int | None, response_headers: dict,
        response_body: str | None, duration_ms: int | None,
        size_bytes: int | None, error: str | None,
    ) -> PechkinRequestHistory:
        entry = PechkinRequestHistory(
            request_id=request_id, resolved_url=resolved_url,
            method=method, request_headers=request_headers,
            request_body=request_body, status_code=status_code,
            response_headers=response_headers, response_body=response_body,
            duration_ms=duration_ms, size_bytes=size_bytes, error=error,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def list_history(
        self, request_id: str, limit: int = 20,
    ) -> list[PechkinRequestHistory]:
        stmt = (
            select(PechkinRequestHistory)
            .where(PechkinRequestHistory.request_id == request_id)
            .order_by(PechkinRequestHistory.executed_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_recent_history(
        self, project_id: str, limit: int = 100,
    ) -> list[PechkinRequestHistory]:
        stmt = (
            select(PechkinRequestHistory)
            .join(PechkinRequest, PechkinRequestHistory.request_id == PechkinRequest.id)
            .join(PechkinCollection, PechkinRequest.collection_id == PechkinCollection.id)
            .where(PechkinCollection.project_id == project_id)
            .order_by(PechkinRequestHistory.executed_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def trim_history(self, request_id: str, keep: int = 50) -> int:
        """Delete oldest history entries, keeping only `keep` most recent."""
        subq = (
            select(PechkinRequestHistory.id)
            .where(PechkinRequestHistory.request_id == request_id)
            .order_by(PechkinRequestHistory.executed_at.desc())
            .limit(keep)
            .subquery()
        )
        stmt = (
            delete(PechkinRequestHistory)
            .where(
                PechkinRequestHistory.request_id == request_id,
                PechkinRequestHistory.id.notin_(select(subq.c.id)),
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def clear_history(self, request_id: str) -> int:
        stmt = delete(PechkinRequestHistory).where(
            PechkinRequestHistory.request_id == request_id,
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
