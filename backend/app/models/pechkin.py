"""Pechkin (HTTP client) models — Postman-like collections."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class PechkinCollection(Base):
    __tablename__ = "pechkin_collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_variables: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    folders: Mapped[list["PechkinFolder"]] = relationship(
        "PechkinFolder",
        back_populates="collection",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(PechkinFolder.collection_id == PechkinCollection.id,"
            " PechkinFolder.parent_id == None)"
        ),
    )
    requests: Mapped[list["PechkinRequest"]] = relationship(
        "PechkinRequest",
        back_populates="collection",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(PechkinRequest.collection_id == PechkinCollection.id,"
            " PechkinRequest.folder_id == None)"
        ),
    )
    variables: Mapped[list["PechkinVariable"]] = relationship(
        "PechkinVariable", back_populates="collection", cascade="all, delete-orphan",
    )


class PechkinFolder(Base):
    __tablename__ = "pechkin_folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pechkin_collections.id", ondelete="CASCADE"), index=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pechkin_folders.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    collection: Mapped["PechkinCollection"] = relationship(
        "PechkinCollection", back_populates="folders",
    )
    children: Mapped[list["PechkinFolder"]] = relationship(
        "PechkinFolder", cascade="all, delete-orphan",
    )
    requests: Mapped[list["PechkinRequest"]] = relationship(
        "PechkinRequest", back_populates="folder", cascade="all, delete-orphan",
    )


class PechkinRequest(Base):
    """Saved HTTP request."""

    __tablename__ = "pechkin_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pechkin_collections.id", ondelete="CASCADE"), index=True,
    )
    folder_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pechkin_folders.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10))
    url: Mapped[str] = mapped_column(Text)
    headers: Mapped[dict] = mapped_column(JSON, default=dict)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_type: Mapped[str] = mapped_column(String(30), default="none")
    auth: Mapped[dict] = mapped_column(JSON, default=dict)
    pre_request_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_snippets: Mapped[list] = mapped_column(JSON, default=list)
    extract_variables: Mapped[list] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    collection: Mapped["PechkinCollection"] = relationship(
        "PechkinCollection", back_populates="requests",
    )
    folder: Mapped["PechkinFolder"] = relationship(
        "PechkinFolder", back_populates="requests",
    )
    history: Mapped[list["PechkinRequestHistory"]] = relationship(
        "PechkinRequestHistory",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="PechkinRequestHistory.executed_at.desc()",
    )


class PechkinVariable(Base):
    """Collection or environment variable. Replaces {{varName}} in URL/headers/body."""

    __tablename__ = "pechkin_variables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pechkin_collections.id", ondelete="CASCADE"), index=True,
    )
    scope: Mapped[str] = mapped_column(String(50), default="collection")
    name: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(Text, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    collection: Mapped["PechkinCollection"] = relationship(
        "PechkinCollection", back_populates="variables",
    )


class PechkinRequestHistory(Base):
    """Response history per request."""

    __tablename__ = "pechkin_request_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pechkin_requests.id", ondelete="CASCADE"), index=True,
    )
    resolved_url: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(10))
    request_headers: Mapped[dict] = mapped_column(JSON, default=dict)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict] = mapped_column(JSON, default=dict)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True,
    )

    request: Mapped["PechkinRequest"] = relationship(
        "PechkinRequest", back_populates="history",
    )
