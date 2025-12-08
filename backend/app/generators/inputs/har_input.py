"""HAR (HTTP Archive) input parser."""

from urllib.parse import urlparse, parse_qs
import json
from .base import TestGeneratorInput, EndpointSpec


class HARInput(TestGeneratorInput):
    """Parse HAR data from recorded sessions."""

    def __init__(self, har_data: dict | list):
        if isinstance(har_data, dict) and "log" in har_data:
            self.entries = har_data["log"]["entries"]
        elif isinstance(har_data, list):
            self.entries = har_data
        else:
            self.entries = []
        self._base_url = self._extract_base_url()
        self._auth_config = self._detect_auth()

    def to_endpoints(self) -> list[EndpointSpec]:
        return [ep for entry in self.entries if (ep := self._parse_entry(entry))]

    def get_base_url(self) -> str:
        return self._base_url

    def get_auth_config(self) -> dict | None:
        return self._auth_config

    def _parse_entry(self, entry: dict) -> EndpointSpec | None:
        if "request" not in entry:
            return None

        req = entry["request"]
        if isinstance(req, dict):
            url = req.get("url", "")
            method = req.get("method", "GET")
            headers = {h["name"]: h["value"] for h in req.get("headers", [])} if isinstance(req.get("headers"), list) else req.get("headers", {})
            body = req.get("postData", {}).get("text") if isinstance(req.get("postData"), dict) else req.get("body")
        else:
            return None

        parsed = urlparse(url)
        path = parsed.path or "/"

        request_body = None
        if body:
            try:
                request_body = json.loads(body) if isinstance(body, str) else body
            except json.JSONDecodeError:
                request_body = {"raw": body}

        parameters = None
        if parsed.query:
            parameters = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}

        return EndpointSpec(
            method=method.upper(),
            path=path,
            parameters=parameters,
            request_body=request_body,
            headers=headers,
            auth_type=self._detect_auth_type(headers),
        )

    def _extract_base_url(self) -> str:
        if not self.entries:
            return "http://localhost"
        entry = self.entries[0]
        if "request" in entry:
            url = entry["request"].get("url", "") if isinstance(entry["request"], dict) else ""
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return "http://localhost"

    def _detect_auth_type(self, headers: dict) -> str | None:
        headers_lower = {k.lower(): v for k, v in headers.items()}
        if "authorization" in headers_lower:
            auth = headers_lower["authorization"]
            if auth.lower().startswith("bearer"):
                return "bearer"
            elif auth.lower().startswith("basic"):
                return "basic"
        if "x-api-key" in headers_lower:
            return "api_key"
        return None

    def _detect_auth(self) -> dict | None:
        for entry in self.entries:
            if "request" not in entry:
                continue
            url = entry["request"].get("url", "") if isinstance(entry["request"], dict) else ""
            if any(p in url.lower() for p in ["/login", "/auth", "/token", "/signin"]):
                return {"type": "login_endpoint", "url": url}
        return None
