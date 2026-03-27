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
        self._headers = {"Authorization": f"Bearer {self.token}"}

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

    def start_launch(self, total_expected: int = 0) -> str:
        """POST /ingest/start → returns launch_id."""
        try:
            resp = httpx.post(
                f"{self.url}/api/v1/launches/ingest/start",
                json={
                    "launch_name": self.launch_name,
                    "branch": self.branch,
                    "environment": self.environment,
                    "pipeline_id": self.pipeline_id,
                    "project_id": self.project_id,
                    "total_expected": total_expected,
                },
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            launch_id = resp.json()["launch_id"]
            logger.info(f"errorlens: started launch {launch_id}")
            return launch_id
        except Exception as e:
            logger.error(f"errorlens: failed to start launch: {e}")
            return ""

    def send_batch(self, launch_id: str, tests: list[dict]) -> None:
        """POST /ingest/batch → append tests to running launch."""
        try:
            resp = httpx.post(
                f"{self.url}/api/v1/launches/ingest/batch",
                json={
                    "launch_id": launch_id,
                    "project_id": self.project_id,
                    "tests": tests,
                },
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                f"errorlens: batch +{len(tests)} → {data['total']} total "
                f"({data['passed']}P/{data['failed']}F/{data['skipped']}S)"
            )
        except Exception as e:
            logger.error(f"errorlens: failed to send batch: {e}")

    def finish_launch(self, launch_id: str) -> None:
        """POST /ingest/finish → finalize the launch."""
        try:
            resp = httpx.post(
                f"{self.url}/api/v1/launches/ingest/finish",
                json={
                    "launch_id": launch_id,
                    "project_id": self.project_id,
                },
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                f"errorlens: launch finished → {data['status']} "
                f"({data['total']} tests, {data.get('duration_ms', 0)}ms)"
            )
        except Exception as e:
            logger.error(f"errorlens: failed to finish launch: {e}")

    def send(self, tests: list[dict]) -> None:
        """Legacy: send all tests at once via /ingest (non-streaming)."""
        try:
            resp = httpx.post(
                f"{self.url}/api/v1/launches/ingest",
                json={
                    "launch_name": self.launch_name,
                    "branch": self.branch,
                    "environment": self.environment,
                    "pipeline_id": self.pipeline_id,
                    "project_id": self.project_id,
                    "tests": tests,
                },
                headers=self._headers,
                timeout=30,
            )
            resp.raise_for_status()
            logger.info(f"errorlens: reported {len(tests)} tests -> {self.url}")
        except Exception as e:
            logger.error(f"errorlens: failed to send report: {e}")
