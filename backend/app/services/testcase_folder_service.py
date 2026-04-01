"""TestCase folder service - business logic with depth validation."""

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TestCaseFolder
from app.repositories.testcase_folder_repo import TestCaseFolderRepository
from app.repositories.testcase_repo import TestCaseRepository

MAX_DEPTH = 3


class TestCaseFolderService:
    """Service for test case folder operations with depth validation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TestCaseFolderRepository(db)
        self.testcase_repo = TestCaseRepository(db)

    async def create_folder(
        self,
        name: str,
        project_id: str,
        parent_id: str | None = None,
    ) -> TestCaseFolder:
        """Create folder with depth and uniqueness validation."""
        if parent_id:
            parent = await self.repo.get_by_id(parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Parent folder not found")
            parent_depth = await self.repo.get_depth(parent_id)
            if parent_depth >= MAX_DEPTH:
                raise HTTPException(
                    status_code=400, detail="Maximum nesting depth is 3"
                )

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
        """Get full folder tree with test cases."""
        return await self.repo.get_tree(project_id)

    async def update_folder(
        self, folder_id: str, name: str, project_id: str
    ) -> TestCaseFolder:
        """Update folder name with uniqueness check."""
        folder = await self.repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

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
        """Delete folder. Test cases move to parent folder (or root)."""
        folder = await self.repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        testcases = await self.testcase_repo.get_many_by_field(
            "folder_id", folder_id, limit=10000
        )
        for tc in testcases:
            tc.folder_id = folder.parent_id

        await self.repo.delete(folder_id)
        await self.db.commit()

    async def move_folder(
        self, folder_id: str, new_parent_id: str | None
    ) -> TestCaseFolder:
        """Move folder to new parent with validation."""
        folder = await self.repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        if new_parent_id == folder_id:
            raise HTTPException(
                status_code=400, detail="Cannot move folder into itself"
            )

        if new_parent_id:
            descendants = await self.repo.get_descendants(folder_id)
            if new_parent_id in descendants:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot move folder into its descendant",
                )

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

    async def move_testcase_to_folder(
        self, testcase_id: str, folder_id: str | None
    ) -> None:
        """Move test case to a folder (or root if folder_id is None)."""
        testcase = await self.testcase_repo.get_by_id(testcase_id)
        if not testcase:
            raise HTTPException(status_code=404, detail="Test case not found")

        if folder_id:
            folder = await self.repo.get_by_id(folder_id)
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")

        testcase.folder_id = folder_id
        await self.db.commit()

    def _folder_to_tree(self, folder: TestCaseFolder) -> dict[str, Any]:
        """Convert folder to nested tree dict."""
        children = sorted(
            folder.children, key=lambda f: (f.sort_order, f.name)
        )
        test_cases = sorted(
            folder.test_cases, key=lambda tc: tc.title
        )
        return {
            "id": folder.id,
            "name": folder.name,
            "parent_id": folder.parent_id,
            "sort_order": folder.sort_order,
            "children": [self._folder_to_tree(c) for c in children],
            "test_cases": [
                {
                    "id": tc.id,
                    "title": tc.title,
                    "status": tc.status,
                    "priority": tc.priority,
                    "automation_status": tc.automation_status,
                    "created_at": tc.created_at.isoformat() if tc.created_at else None,
                }
                for tc in test_cases
            ],
            "test_cases_count": len(test_cases),
            "children_count": len(children),
        }
