"""Pechkin service — business logic for HTTP client collections."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pechkin_repo import PechkinRepository
from app.services.pechkin_executor import run_script
from app.services.pechkin_proxy import ProxyRequest, ProxyResponse, execute_proxy

logger = logging.getLogger(__name__)


class PechkinService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PechkinRepository(db)

    # ── Execute ──────────────────────────────────────────────────

    async def execute_request(
        self,
        method: str,
        url: str,
        headers: dict,
        body: str | None,
        body_type: str,
        auth: dict,
        variables: dict,
        timeout: int = 30,
        request_id: str | None = None,
    ) -> ProxyResponse:
        """Execute HTTP request through proxy, optionally save history."""
        req = ProxyRequest(
            method=method, url=url, headers=headers,
            body=body, body_type=body_type, auth=auth,
            variables=variables, timeout=timeout,
        )
        resp = await execute_proxy(req)

        if request_id:
            await self.repo.add_history(
                request_id=request_id,
                resolved_url=url,
                method=method,
                request_headers=headers,
                request_body=body,
                status_code=resp.status_code,
                response_headers=resp.headers,
                response_body=resp.body,
                duration_ms=resp.duration_ms,
                size_bytes=resp.size_bytes,
                error=resp.error,
            )
            await self.repo.trim_history(request_id, keep=50)

        return resp

    async def run_pre_request(self, code: str, request_context: dict) -> dict:
        """Run pre-request script."""
        return await run_script(code, {"request": request_context})

    async def run_test_script(
        self, code: str, request_context: dict, response_context: dict,
    ) -> dict:
        """Run test script with response data."""
        return await run_script(code, {
            "request": request_context,
            "response": response_context,
        })

    # ── Collection runner ────────────────────────────────────────

    async def run_collection(
        self,
        collection_id: str,
        request_ids: list[str] | None = None,
        delay_ms: int = 0,
        stop_on_error: bool = False,
        iterations: int = 1,
        variables: dict | None = None,
    ) -> list[dict]:
        """Run collection requests sequentially."""
        all_requests = await self.repo.list_all_requests(collection_id)
        if request_ids:
            id_set = set(request_ids)
            all_requests = [r for r in all_requests if r.id in id_set]

        # Build variables from collection
        col_vars = await self.repo.list_variables(collection_id)
        merged_vars = {
            v.name: v.value for v in col_vars if v.is_enabled
        }
        if variables:
            merged_vars.update(variables)

        results = []
        for iteration in range(iterations):
            for req in all_requests:
                req_vars = dict(merged_vars)
                resp = await self.execute_request(
                    method=req.method, url=req.url,
                    headers=req.headers or {}, body=req.body,
                    body_type=req.body_type or "none",
                    auth=req.auth or {}, variables=req_vars,
                    request_id=req.id,
                )

                entry: dict = {
                    "iteration": iteration + 1,
                    "request_id": req.id,
                    "request_name": req.name,
                    "status_code": resp.status_code,
                    "duration_ms": resp.duration_ms,
                    "error": resp.error,
                    "tests": None,
                }

                # Extract variables from response
                if req.extract_variables:
                    self._extract_vars(resp, req.extract_variables, merged_vars)

                # Run test script
                if req.test_script:
                    test_result = await self.run_test_script(
                        req.test_script,
                        {"method": req.method, "url": req.url, "headers": req.headers},
                        {
                            "status_code": resp.status_code,
                            "headers": resp.headers,
                            "body": resp.body,
                        },
                    )
                    entry["tests"] = test_result

                results.append(entry)

                if stop_on_error and (resp.error or resp.status_code >= 400):
                    return results

                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000)

        return results

    @staticmethod
    def _extract_vars(
        resp: ProxyResponse, extract_rules: list, variables: dict,
    ) -> None:
        """Extract variables from response based on rules."""
        import json as json_mod

        for rule in extract_rules:
            name = rule.get("name")
            source = rule.get("source", "body")
            path = rule.get("path", "")
            if not name:
                continue
            try:
                if source == "header":
                    variables[name] = resp.headers.get(path, "")
                elif source == "body":
                    data = json_mod.loads(resp.body)
                    for key in path.split("."):
                        if isinstance(data, dict):
                            data = data.get(key, "")
                        else:
                            data = ""
                            break
                    variables[name] = str(data)
            except (json_mod.JSONDecodeError, AttributeError):
                logger.warning(f"Failed to extract variable {name} from response")
