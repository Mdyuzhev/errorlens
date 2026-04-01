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

    async def get_tree(self, project_id: str) -> list[dict]:
        """Get full folder tree as dicts (flat query + Python assembly)."""
        from app.models.testcase import TestCase as TC

        # Load all folders flat
        q_folders = (
            select(TestCaseFolder)
            .where(TestCaseFolder.project_id == project_id)
            .order_by(TestCaseFolder.sort_order, TestCaseFolder.name)
        )
        result = await self.session.execute(q_folders)
        all_folders = list(result.scalars().all())

        # Load all test cases for this project (id, title, status, priority, folder_id)
        q_tc = (
            select(TC.id, TC.title, TC.status, TC.priority, TC.human_id, TC.folder_id)
            .where(TC.project_id == project_id)
            .order_by(TC.title)
        )
        tc_result = await self.session.execute(q_tc)
        tc_rows = tc_result.all()

        # Group test cases by folder_id
        tc_by_folder: dict[str, list[dict]] = {}
        for row in tc_rows:
            fid = row[5]
            if fid:
                tc_by_folder.setdefault(fid, []).append({
                    "id": row[0], "title": row[1], "status": row[2],
                    "priority": row[3], "human_id": row[4],
                })

        # Build dict nodes
        nodes: dict[str, dict] = {}
        for f in all_folders:
            nodes[f.id] = {
                "id": f.id,
                "name": f.name,
                "parent_id": f.parent_id,
                "sort_order": f.sort_order,
                "children": [],
                "test_cases": tc_by_folder.get(f.id, []),
            }

        # Assemble tree
        roots = []
        for f in all_folders:
            node = nodes[f.id]
            if f.parent_id and f.parent_id in nodes:
                nodes[f.parent_id]["children"].append(node)
            else:
                roots.append(node)

        # Calculate test_cases_count recursively (own + descendants)
        def calc_count(node: dict) -> int:
            own = len(node["test_cases"])
            for child in node["children"]:
                own += calc_count(child)
            node["test_cases_count"] = own
            return own

        for root in roots:
            calc_count(root)

        return roots

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
