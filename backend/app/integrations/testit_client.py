"""TestIt TMS Integration Client."""

import httpx
from typing import Optional
from pydantic import BaseModel
from app.config import settings


class TestItStep(BaseModel):
    """Step in TestIt test case."""

    action: str
    expected: str
    test_data: Optional[str] = None


class TestItTestCase(BaseModel):
    """TestIt test case model."""

    name: str
    description: str = ""
    preconditions: str = ""
    postconditions: str = ""
    priority: str = "Medium"  # Lowest, Low, Medium, High, Highest
    state: str = "Ready"  # NeedsWork, NotReady, Ready
    steps: list[TestItStep] = []
    tags: list[str] = []
    section_id: Optional[str] = None


class TestItClient:
    """Client for TestIt API."""

    def __init__(
        self,
        url: str = None,
        token: str = None,
        project_id: str = None,
    ):
        self.url = (url or settings.testit_url).rstrip("/")
        self.token = token or settings.testit_token
        self.project_id = project_id or settings.testit_project_id

        self.headers = {
            "Authorization": f"PrivateToken {self.token}",
            "Content-Type": "application/json",
        }

    async def check_connection(self) -> dict:
        """Test API connection."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.url}/api/v2/projects/{self.project_id}",
                    headers=self.headers,
                    timeout=10,
                )
                if response.status_code == 200:
                    data = response.json()
                    return {"connected": True, "project_name": data.get("name", "Unknown")}
                else:
                    return {
                        "connected": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                    }
            except Exception as e:
                return {"connected": False, "error": str(e)}

    async def get_sections(self) -> list:
        """Get all sections (folders) in project."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/api/v2/projects/{self.project_id}/sections",
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
            return []

    async def create_section(self, name: str, parent_id: str = None) -> dict:
        """Create a new section (folder)."""
        payload = {"name": name, "projectId": self.project_id}
        if parent_id:
            payload["parentId"] = parent_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/api/v2/sections",
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            return response.json()

    async def get_or_create_section(self, name: str = "ErrorLens") -> str:
        """Get existing section or create new one."""
        sections = await self.get_sections()

        for section in sections:
            if section.get("name") == name:
                return section.get("id")

        # Create new section
        new_section = await self.create_section(name)
        return new_section.get("id")

    async def create_test_case(self, test_case: TestItTestCase) -> dict:
        """
        Create a test case in TestIt.

        Returns:
            dict with 'id' and 'globalId' of created test case
        """
        # Get or create ErrorLens section
        section_id = test_case.section_id or await self.get_or_create_section("ErrorLens")

        # Build steps payload
        steps = []
        for step in test_case.steps:
            steps.append(
                {
                    "action": step.action,
                    "expected": step.expected,
                    "testData": step.test_data or "",
                    "comments": "",
                    "workItemId": None,
                }
            )

        # Build preconditions steps
        precondition_steps = []
        if test_case.preconditions:
            for line in test_case.preconditions.split("\n"):
                line = line.strip()
                if line and not line.startswith("-"):
                    precondition_steps.append(
                        {"action": line, "expected": "", "testData": "", "comments": ""}
                    )
                elif line.startswith("- "):
                    precondition_steps.append(
                        {"action": line[2:], "expected": "", "testData": "", "comments": ""}
                    )

        # Build payload
        payload = {
            "entityTypeName": "TestCases",
            "projectId": self.project_id,
            "sectionId": section_id,
            "name": test_case.name,
            "description": test_case.description,
            "state": test_case.state,
            "priority": test_case.priority,
            "steps": steps,
            "preconditionSteps": precondition_steps,
            "postconditionSteps": [],
            "tags": [{"name": tag} for tag in test_case.tags],
            "attributes": {},
            "duration": 300000,  # 5 minutes default
            "links": [],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/api/v2/workItems",
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 201):
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "globalId": data.get("globalId"),
                    "url": f"{self.url}/projects/{self.project_id}/tests/{data.get('globalId')}",
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }


# Singleton client (uses default settings)
testit_client = TestItClient()
