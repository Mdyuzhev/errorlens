"""Base generator class and shared utilities for test code generation."""

import json
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from app.models_pydantic import RecordedHttpExchange


class BaseGenerator(ABC):
    """Abstract base class for all test generators."""

    def __init__(self, recorded_requests: list[RecordedHttpExchange]):
        self.requests = recorded_requests
        self.base_url = self._extract_base_url()
        self.has_auth_flow = self._detect_auth_flow()

    def _extract_base_url(self) -> str:
        """Extract base URL from first request."""
        if not self.requests:
            return "http://localhost"
        first_url = self.requests[0].request.url
        parsed = urlparse(first_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _detect_auth_flow(self) -> bool:
        """Detect if session has authentication flow (login -> token -> use token)."""
        has_login = False
        has_auth_header = False

        for exchange in self.requests:
            req = exchange.request
            if is_auth_endpoint(req.url):
                has_login = True
            if has_auth_header_in_request(req.headers):
                has_auth_header = True

        return has_login and has_auth_header

    @abstractmethod
    def generate(self) -> str:
        """Generate test code. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Return file extension for generated code (e.g., '.py', '.java')."""
        pass

    @abstractmethod
    def get_language(self) -> str:
        """Return language name (e.g., 'python', 'java', 'javascript')."""
        pass


# =============================================================================
# Shared utility functions
# =============================================================================


def is_auth_endpoint(url: str) -> bool:
    """Check if URL is an authentication endpoint."""
    path = urlparse(url).path.lower()
    auth_patterns = ["/login", "/auth", "/signin", "/token", "/oauth", "/session"]
    return any(pattern in path for pattern in auth_patterns)


def has_auth_header_in_request(headers: dict) -> bool:
    """Check if request has authorization header."""
    auth_headers = {"authorization", "x-api-key", "x-auth-token", "x-access-token"}
    return any(h.lower() in auth_headers for h in headers.keys())


def filter_headers(
    headers: dict, exclude_auth: bool = False, exclude_standard: bool = True
) -> dict:
    """
    Filter headers for generated code.

    Args:
        headers: Original headers dict
        exclude_auth: Remove auth headers (when handled separately)
        exclude_standard: Remove standard browser headers
    """
    skip = set()

    if exclude_standard:
        skip.update(
            {
                "host",
                "connection",
                "accept-encoding",
                "content-length",
                "user-agent",
                "cookie",
                "origin",
                "referer",
                "sec-ch-ua",
                "sec-ch-ua-mobile",
                "sec-ch-ua-platform",
                "sec-fetch-dest",
                "sec-fetch-mode",
                "sec-fetch-site",
            }
        )

    if exclude_auth:
        skip.update({"authorization", "x-api-key", "x-auth-token", "x-access-token"})

    return {k: v for k, v in headers.items() if k.lower() not in skip}


def generate_method_name(method: str, url: str, index: int) -> str:
    """Generate readable method/function name from URL path."""
    path = urlparse(url).path or "/"
    # Take last 2 meaningful path segments
    parts = [p for p in path.split("/") if p and not p.isdigit() and len(p) < 30][-2:]

    if parts:
        # CamelCase for Java, snake_case will be converted by caller if needed
        name = "".join(word.capitalize() for word in parts)
        return f"{method.lower()}{name}"

    return f"{method.lower()}Request{index + 1}"


def extract_path(url: str) -> str:
    """Extract path from full URL."""
    return urlparse(url).path or "/"


def parse_json_body(body: str | None) -> dict | None:
    """Try to parse body as JSON, return None if not JSON."""
    if not body:
        return None
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def escape_string(s: str, quote_char: str = '"') -> str:
    """Escape string for use in generated code."""
    if not s:
        return ""
    # Escape backslashes first, then quotes, then newlines
    result = s.replace("\\", "\\\\")
    result = result.replace(quote_char, f"\\{quote_char}")
    result = result.replace("\n", "\\n")
    result = result.replace("\r", "\\r")
    result = result.replace("\t", "\\t")
    return result


def get_token_field_names() -> list[str]:
    """Common field names for auth tokens in API responses."""
    return ["token", "access_token", "accessToken", "jwt", "id_token", "auth_token"]


def detect_token_in_response(response_body: str | None) -> str | None:
    """Detect which field contains auth token in response."""
    data = parse_json_body(response_body)
    if not data or not isinstance(data, dict):
        return None

    for field in get_token_field_names():
        if field in data and isinstance(data[field], str):
            return field

    return None
