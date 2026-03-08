"""Article folder service - business logic with depth validation."""

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ArticleFolder
from app.repositories.article_folder_repo import ArticleFolderRepository
from app.repositories.article_repo import ArticleRepository

MAX_DEPTH = 3


class ArticleFolderService:
    """Service for article folder operations with depth validation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ArticleFolderRepository(db)
        self.article_repo = ArticleRepository(db)

    async def create_folder(
        self,
        name: str,
        project_id: str,
        parent_id: str | None = None,
    ) -> ArticleFolder:
        """Create folder with depth and uniqueness validation."""
        # Validate depth
        if parent_id:
            parent = await self.repo.get_by_id(parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Parent folder not found")
            parent_depth = await self.repo.get_depth(parent_id)
            if parent_depth >= MAX_DEPTH:
                raise HTTPException(
                    status_code=400, detail="Maximum nesting depth is 3"
                )

        # Check duplicate name
        existing = await self.repo.get_by_name_and_parent(name, parent_id, project_id)
        if existing:
            raise HTTPException(
                status_code=400, detail="Folder with this name already exists"
            )

        folder = await self.repo.create({
            "name": name,
            "parent_id": parent_id,
            "project_id": project_id,
        })
        await self.db.commit()
        return folder

    async def get_tree(self, project_id: str) -> list[dict[str, Any]]:
        """Get full folder tree with articles."""
        folders = await self.repo.get_tree(project_id)
        return [self._folder_to_tree(f) for f in folders]

    async def update_folder(
        self, folder_id: str, name: str, project_id: str
    ) -> ArticleFolder:
        """Update folder name with uniqueness check."""
        folder = await self.repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        # Check duplicate name in same parent
        existing = await self.repo.get_by_name_and_parent(
            name, folder.parent_id, project_id
        )
        if existing and existing.id != folder_id:
            raise HTTPException(
                status_code=400, detail="Folder with this name already exists"
            )

        folder.name = name
        folder.updated_at = datetime.utcnow()
        await self.db.commit()
        return folder

    async def delete_folder(self, folder_id: str) -> None:
        """Delete folder. Articles move to parent folder (or root)."""
        folder = await self.repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        # Move articles to parent folder (or null if root)
        articles = await self.article_repo.get_many_by_field(
            "folder_id", folder_id, limit=10000
        )
        for article in articles:
            article.folder_id = folder.parent_id

        # Cascade delete handles children
        await self.repo.delete(folder_id)
        await self.db.commit()

    async def move_folder(
        self, folder_id: str, new_parent_id: str | None
    ) -> ArticleFolder:
        """Move folder to new parent with validation."""
        folder = await self.repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        # Cannot move to self
        if new_parent_id == folder_id:
            raise HTTPException(
                status_code=400, detail="Cannot move folder into itself"
            )

        # Cannot move to descendant
        if new_parent_id:
            descendants = await self.repo.get_descendants(folder_id)
            if new_parent_id in descendants:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot move folder into its descendant",
                )

            # Check depth: new_parent depth + subtree depth + 1 <= MAX_DEPTH
            parent_depth = await self.repo.get_depth(new_parent_id)
            subtree_depth = await self.repo.get_max_subtree_depth(folder_id)
            if parent_depth + subtree_depth + 1 > MAX_DEPTH:
                raise HTTPException(
                    status_code=400, detail="Maximum nesting depth is 3"
                )

        folder.parent_id = new_parent_id
        folder.updated_at = datetime.utcnow()
        await self.db.commit()
        return folder

    async def move_article_to_folder(
        self, article_id: str, folder_id: str | None
    ) -> None:
        """Move article to a folder (or root if folder_id is None)."""
        article = await self.article_repo.get_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        if folder_id:
            folder = await self.repo.get_by_id(folder_id)
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")

        article.folder_id = folder_id
        await self.db.commit()

    def _folder_to_tree(self, folder: ArticleFolder) -> dict[str, Any]:
        """Convert folder to nested tree dict."""
        children = sorted(
            folder.children, key=lambda f: (f.sort_order, f.name)
        )
        articles = sorted(
            folder.articles, key=lambda a: a.title
        )
        return {
            "id": folder.id,
            "name": folder.name,
            "parent_id": folder.parent_id,
            "sort_order": folder.sort_order,
            "children": [self._folder_to_tree(c) for c in children],
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "slug": a.slug,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in articles
            ],
            "articles_count": len(articles),
            "children_count": len(children),
        }
