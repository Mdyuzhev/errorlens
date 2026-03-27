"""HTTP client for sending reports to ErrorLens server."""
import logging
import os

import httpx

logger = logging.getLogger(__name__)


class ELClient:
    def __init__(
        self,
        url: str,
        token: str,
        project_id: str,
        launch_name: str = "",
        branch: str = "",
        environment: str = "",
        pipeline_id: str = "",
    ):
        self.url = url.rstrip("/")
        self.token = token
        self.project_id = project_id
        self.launch_name = launch_name
        self.branch = branch
        self.environment = environment
        self.pipeline_id = pipeline_id

    @classmethod
    def from_env(cls) -> "ELClient | None":
        url = os.getenv("EL_URL")
        token = os.getenv("EL_TOKEN")
        project_id = os.getenv("EL_PROJECT_ID")
        if not all([url, token, project_id]):
            logger.warning(
                "errorlens-pytest: EL_URL/EL_TOKEN/EL_PROJECT_ID not set, skipping report"
            )
            return None
        return cls(
            url=url,
            token=token,
            project_id=project_id,
            launch_name=os.getenv("EL_LAUNCH_NAME", ""),
            branch=os.getenv("EL_BRANCH", ""),
            environment=os.getenv("EL_ENVIRONMENT", ""),
            pipeline_id=os.getenv("EL_PIPELINE_ID", ""),
        )

    def send(self, tests: list[dict]) -> None:
        payload = {
            "launch_name": self.launch_name,
            "branch": self.branch,
            "environment": self.environment,
            "pipeline_id": self.pipeline_id,
            "project_id": self.project_id,
            "tests": tests,
        }
        try:
            response = httpx.post(
                f"{self.url}/api/v1/launches/ingest",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"errorlens-pytest: reported {len(tests)} tests -> {self.url}")
        except Exception as e:
            logger.error(f"errorlens-pytest: failed to send report: {e}")
