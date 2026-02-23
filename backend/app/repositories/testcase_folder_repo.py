"""TestCase folder repository - data access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import TestCaseFolder
from app.repositories.base import BaseRepository


class TestCaseFolderRepository(BaseRepository[TestCaseFolder]):
    """Repository for TestCaseFolder CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(TestCaseFolder, db)

    async def get_tree(self, project_id: str) -> list[TestCaseFolder]:
        """Get all root folders with eager-loaded children and test_cases."""
        query = (
            select(TestCaseFolder)
            .where(
                TestCaseFolder.project_id == project_id,
                TestCaseFolder.parent_id.is_(None),
            )
            .options(
                selectinload(TestCaseFolder.children)
                .selectinload(TestCaseFolder.children)
                .selectinload(TestCaseFolder.test_cases),
                selectinload(TestCaseFolder.children)
                .selectinload(TestCaseFolder.test_cases),
                selectinload(TestCaseFolder.children)
                .selectinload(TestCaseFolder.children)
                .selectinload(TestCaseFolder.children),
                selectinload(TestCaseFolder.test_cases),
            )
            .order_by(TestCaseFolder.sort_order, TestCaseFolder.name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_children(self, folder_id: str) -> list[TestCaseFolder]:
        """Get direct children of a folder."""
        query = (
            select(TestCaseFolder)
            .where(TestCaseFolder.parent_id == folder_id)
            .order_by(TestCaseFolder.sort_order, TestCaseFolder.name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_depth(self, folder_id: str) -> int:
        """Calculate depth by traversing parent chain. Root = depth 1."""
        depth = 0
        current_id = folder_id
        while current_id:
            depth += 1
            folder = await self.get_by_id(current_id)
            if not folder:
                break
            current_id = folder.parent_id
        return depth

    async def get_by_name_and_parent(
        self, name: str, parent_id: str | None, project_id: str
    ) -> TestCaseFolder | None:
        """Check if folder with same name exists in same parent."""
        query = select(TestCaseFolder).where(
            TestCaseFolder.name == name,
            TestCaseFolder.project_id == project_id,
        )
        if parent_id:
            query = query.where(TestCaseFolder.parent_id == parent_id)
        else:
            query = query.where(TestCaseFolder.parent_id.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_descendants(self, folder_id: str) -> list[str]:
        """Get all descendant folder IDs recursively."""
        descendants: list[str] = []
        children = await self.get_children(folder_id)
        for child in children:
            descendants.append(child.id)
            descendants.extend(await self.get_descendants(child.id))
        return descendants

    async def get_max_subtree_depth(self, folder_id: str) -> int:
        """Get max depth of subtree below folder. Leaf = 0."""
        children = await self.get_children(folder_id)
        if not children:
            return 0
        max_child_depth = 0
        for child in children:
            child_depth = await self.get_max_subtree_depth(child.id)
            max_child_depth = max(max_child_depth, child_depth + 1)
        return max_child_depth
