"""GitLab API client service."""

from typing import Any

import httpx

from app.models.db_models import GitLabConnection
from app.services.exceptions import GitLabAuthError, GitLabConnectionError
from app.utils.crypto import decrypt_token


class GitLabService:
    """Wraps GitLab REST API v4 via httpx."""

    TIMEOUT = 15.0

    async def _request(
        self,
        connection: GitLabConnection,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make authenticated request to GitLab API."""
        token = decrypt_token(connection.token_encrypted)
        url = f"{connection.url.rstrip('/')}/api/v4{path}"

        try:
            async with httpx.AsyncClient(
                verify=connection.verify_ssl, timeout=self.TIMEOUT
            ) as client:
                response = await client.request(
                    method, url, headers={"PRIVATE-TOKEN": token}, params=params
                )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise GitLabConnectionError(
                f"Cannot connect to {connection.url}: {exc}"
            ) from exc

        if response.status_code == 401:
            raise GitLabAuthError("Invalid or expired GitLab token")

        response.raise_for_status()
        return response.json()

    async def check_connection(
        self, connection: GitLabConnection
    ) -> dict[str, Any]:
        """Check connection by fetching current user."""
        try:
            data = await self._request(connection, "GET", "/user")
            return {"ok": True, "username": data.get("username", "")}
        except GitLabAuthError:
            return {"ok": False, "error": "Invalid or expired token"}
        except GitLabConnectionError as exc:
            return {"ok": False, "error": str(exc)}

    async def get_projects(
        self, connection: GitLabConnection
    ) -> list[dict[str, Any]]:
        """List GitLab projects the token has access to."""
        data = await self._request(
            connection, "GET", "/projects",
            params={"membership": "true", "per_page": 50, "order_by": "name"},
        )
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "path_with_namespace": p["path_with_namespace"],
                "web_url": p["web_url"],
                "default_branch": p.get("default_branch", "main"),
            }
            for p in data
        ]

    async def get_pipelines(
        self,
        connection: GitLabConnection,
        project_id: int,
        ref: str | None = None,
    ) -> list[dict[str, Any]]:
        """List pipelines for a GitLab project."""
        params: dict[str, Any] = {"per_page": 20}
        if ref:
            params["ref"] = ref
        data = await self._request(
            connection, "GET", f"/projects/{project_id}/pipelines", params=params
        )
        return [
            {
                "id": p["id"],
                "status": p["status"],
                "ref": p["ref"],
                "created_at": p["created_at"],
                "web_url": p["web_url"],
            }
            for p in data
        ]

    async def get_branches(
        self, connection: GitLabConnection, project_id: int
    ) -> list[str]:
        """List branch names for a GitLab project."""
        data = await self._request(
            connection, "GET", f"/projects/{project_id}/repository/branches",
            params={"per_page": 100},
        )
        return [b["name"] for b in data]
