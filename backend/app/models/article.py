"""Article, ArticleFolder, ArticleImage models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class ArticleFolder(Base):
    """Folder for organizing articles in a tree hierarchy (max depth 3)."""

    __tablename__ = "article_folders"
    __table_args__ = (
        UniqueConstraint("name", "parent_id", "project_id", name="uq_article_folder_name_parent_project"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200))

    # Parent folder (self-reference)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("article_folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Multi-tenancy
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="article_folders")
    parent: Mapped[Optional["ArticleFolder"]] = relationship(
        "ArticleFolder", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["ArticleFolder"]] = relationship(
        "ArticleFolder", back_populates="parent", cascade="all, delete-orphan"
    )
    articles: Mapped[list["Article"]] = relationship(
        "Article", back_populates="article_folder"
    )

    def __repr__(self) -> str:
        return f"<ArticleFolder {self.name}>"


class Article(Base):
    """Knowledge base article."""

    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    human_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    content: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Multi-tenancy
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Folder (tree structure)
    folder_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("article_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Organization
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=list)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # Metadata
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Stats
    views: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="articles")
    article_folder: Mapped[Optional["ArticleFolder"]] = relationship(
        "ArticleFolder", back_populates="articles"
    )
    images: Mapped[list["ArticleImage"]] = relationship(
        "ArticleImage", back_populates="article"
    )


class ArticleImage(Base):
    """Image attached to an article, stored in S3/MinIO."""

    __tablename__ = "article_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    original_filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Multi-tenancy
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )

    # Link to article (optional — image can be orphan before insertion)
    article_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )

    # Audit
    uploaded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    article: Mapped[Optional["Article"]] = relationship("Article", back_populates="images")

    def __repr__(self) -> str:
        return f"<ArticleImage {self.object_key}>"
