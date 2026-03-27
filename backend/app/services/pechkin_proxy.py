"""Pechkin HTTP proxy — resolves variables and executes requests via httpx."""

import base64
import re
import time
from dataclasses import dataclass

import httpx

VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def resolve_variables(text: str, variables: dict[str, str]) -> str:
    """Replace {{varName}} placeholders with variable values."""
    return VARIABLE_PATTERN.sub(
        lambda m: variables.get(m.group(1), m.group(0)), text,
    )


@dataclass
class ProxyRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: str | None
    body_type: str  # none | raw | form-data | x-www-form-urlencoded
    auth: dict
    variables: dict[str, str]
    timeout: int = 30


@dataclass
class ProxyResponse:
    status_code: int
    status_text: str
    headers: dict[str, str]
    body: str
    duration_ms: int
    size_bytes: int
    error: str | None = None


async def execute_proxy(req: ProxyRequest) -> ProxyResponse:
    """Execute an HTTP request through the proxy with variable resolution."""
    url = resolve_variables(req.url, req.variables)
    headers = {k: resolve_variables(v, req.variables) for k, v in req.headers.items()}
    body = resolve_variables(req.body, req.variables) if req.body else None

    # Apply auth
    auth_type = req.auth.get("type")
    if auth_type == "bearer":
        token = resolve_variables(req.auth.get("token", ""), req.variables)
        headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic":
        username = req.auth.get("username", "")
        password = req.auth.get("password", "")
        creds = f"{username}:{password}"
        headers["Authorization"] = f"Basic {base64.b64encode(creds.encode()).decode()}"
    elif auth_type == "api_key":
        key_name = req.auth.get("key", "X-API-Key")
        key_value = resolve_variables(req.auth.get("value", ""), req.variables)
        if req.auth.get("in") == "query":
            separator = "&" if "?" in url else "?"
            url += f"{separator}{key_name}={key_value}"
        else:
            headers[key_name] = key_value

    # Build content
    content = None
    if body and req.body_type == "raw":
        content = body.encode()
    elif req.body_type == "x-www-form-urlencoded" and body:
        content = body.encode()
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, verify=False, timeout=req.timeout,
        ) as client:
            response = await client.request(
                method=req.method.upper(), url=url,
                headers=headers, content=content,
            )
        duration = int((time.perf_counter() - start) * 1000)
        return ProxyResponse(
            status_code=response.status_code,
            status_text=response.reason_phrase or "",
            headers=dict(response.headers),
            body=response.text,
            duration_ms=duration,
            size_bytes=len(response.content),
        )
    except httpx.HTTPError as e:
        duration = int((time.perf_counter() - start) * 1000)
        return ProxyResponse(
            status_code=0, status_text="Error",
            headers={}, body="",
            duration_ms=duration, size_bytes=0,
            error=str(e),
        )
    except OSError as e:
        duration = int((time.perf_counter() - start) * 1000)
        return ProxyResponse(
            status_code=0, status_text="Error",
            headers={}, body="",
            duration_ms=duration, size_bytes=0,
            error=str(e),
        )
