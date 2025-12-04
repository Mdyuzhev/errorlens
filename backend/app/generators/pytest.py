"""Generate pytest test files from recorded HTTP sessions."""

import json
import logging
from urllib.parse import urlparse

from app.models_pydantic import RecordedHttpExchange
from .base import (
    BaseGenerator,
    is_auth_endpoint,
    filter_headers,
    extract_path,
    parse_json_body,
    get_token_field_names,
)
from .llm_comments import generate_llm_comments

logger = logging.getLogger(__name__)


class PytestGenerator(BaseGenerator):
    """Generate pytest test files from recorded HTTP sessions."""

    def __init__(
        self,
        recorded_requests: list[RecordedHttpExchange],
        test_name: str = "test_session",
        llm_comments: dict[int, str] | None = None,
    ):
        super().__init__(recorded_requests)
        self.test_name = test_name
        self.llm_comments = llm_comments or {}
        self.auth_index = -1
        self.token_field = None
        self.needs_auth_indices = set()
        self._detect_auth_flow_details()

    def get_file_extension(self) -> str:
        return ".py"

    def get_language(self) -> str:
        return "python"

    def _detect_auth_flow_details(self):
        """Detect auth request index and token field."""
        for i, exchange in enumerate(self.requests):
            is_auth, field = self._detect_auth_request(exchange)
            if is_auth and field:
                self.auth_index = i
                self.token_field = field
                break

        if self.auth_index >= 0:
            self.needs_auth_indices = self._detect_requests_needing_auth()

    def _detect_auth_request(self, exchange: RecordedHttpExchange) -> tuple[bool, str | None]:
        """Detect if request is authentication and which field contains token."""
        req = exchange.request
        resp = exchange.response

        if not is_auth_endpoint(req.url) or resp.status != 200:
            return False, None

        # Try to find token in response
        resp_body = parse_json_body(resp.body)
        if resp_body and isinstance(resp_body, dict):
            for field in get_token_field_names():
                if field in resp_body:
                    return True, field

        return is_auth_endpoint(req.url), None

    def _detect_requests_needing_auth(self) -> set[int]:
        """Detect which requests after auth likely need token."""
        needs_auth = set()

        for i, exchange in enumerate(self.requests):
            if i <= self.auth_index:
                continue

            path = urlparse(exchange.request.url).path.lower()
            public_patterns = ['health', 'ping', 'status', 'public', 'version']
            if any(p in path for p in public_patterns):
                continue

            if '/api/' in path or exchange.request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                needs_auth.add(i)

        return needs_auth

    def _generate_method_name(self, method: str, url: str) -> str:
        """Generate readable method name from URL."""
        path = urlparse(url).path or "/"
        parts = [p for p in path.split("/") if p and not p.isdigit()][-2:]
        if parts:
            name = "_".join(parts).replace("-", "_").replace(".", "_")
            name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
            return f"{method.lower()}_{name}"
        return f"{method.lower()}_request"

    def generate(self) -> str:
        """Generate pytest test file."""
        if not self.requests:
            return self._empty_template()

        lines = self._generate_header()
        lines.extend(self._generate_fixtures())
        lines.extend(self._generate_helpers())
        lines.extend(self._generate_test_class())
        lines.extend(self._generate_main_block())

        return "\n".join(lines)

    def _generate_header(self) -> list[str]:
        """Generate file header with imports."""
        return [
            '"""',
            "Auto-generated pytest tests from ErrorLens session.",
            "",
            "Run with: pytest {}.py -v".format(self.test_name),
            "Or simply: python {}.py".format(self.test_name),
            "",
            "Environment variables:",
            "  BASE_URL - Override base URL (default: recorded URL)",
            '"""',
            "",
            "import os",
            "import sys",
            "import requests",
            "import pytest",
            "",
            "",
            "# =============================================================================",
            "# Configuration",
            "# =============================================================================",
            "",
            f'BASE_URL = os.environ.get("BASE_URL", "{self.base_url}")',
            "",
        ]

    def _generate_fixtures(self) -> list[str]:
        """Generate pytest fixtures."""
        return [
            "",
            "# =============================================================================",
            "# Health Check Fixture",
            "# =============================================================================",
            "",
            "@pytest.fixture(scope='session', autouse=True)",
            "def check_server_available():",
            '    """Check if API server is reachable before running tests."""',
            "    try:",
            "        response = requests.get(BASE_URL, timeout=5)",
            "    except requests.exceptions.ConnectionError:",
            "        pytest.exit(",
            '            f"API server unavailable at {BASE_URL}. Start the server or set BASE_URL env variable.",',
            "            returncode=1",
            "        )",
            "    except requests.exceptions.Timeout:",
            "        pytest.exit(",
            '            f"API server timeout at {BASE_URL}. Server may be overloaded.",',
            "            returncode=1",
            "        )",
            "",
        ]

    def _generate_helpers(self) -> list[str]:
        """Generate helper functions."""
        return [
            "",
            "# =============================================================================",
            "# Helper Functions",
            "# =============================================================================",
            "",
            "def assert_json_response(response, context=''):",
            '    """Assert response is JSON and return parsed data."""',
            "    content_type = response.headers.get('Content-Type', '')",
            "    if 'application/json' not in content_type:",
            "        text = response.text[:500]",
            "        if '<!DOCTYPE' in text or '<html' in text:",
            "            pytest.fail(",
            '                f"{context}Server returned HTML instead of JSON. "',
            '                f"Status: {response.status_code}, Content-Type: {content_type}"',
            "            )",
            "        pytest.fail(",
            '            f"{context}Expected JSON response, got {content_type}: {text[:200]}"',
            "        )",
            "    return response.json()",
            "",
        ]

    def _generate_test_class(self) -> list[str]:
        """Generate test class with all test methods."""
        lines = [
            "",
            "# =============================================================================",
            "# Test Class",
            "# =============================================================================",
            "",
            "class TestSession:",
            '    """Tests generated from recorded browser session."""',
            "",
        ]

        # Add token class variable if auth detected
        if self.auth_index >= 0 and self.token_field:
            lines.append("    # Shared auth token extracted from login response")
            lines.append("    token = None")
            lines.append("")

        # Generate test methods
        for i, exchange in enumerate(self.requests):
            lines.extend(self._generate_test_method(i, exchange))

        return lines

    def _generate_test_method(self, index: int, exchange: RecordedHttpExchange) -> list[str]:
        """Generate a single test method."""
        req = exchange.request
        resp = exchange.response
        method_name = self._generate_method_name(req.method, req.url)
        path = extract_path(req.url)
        query = urlparse(req.url).query
        full_path = f"{path}?{query}" if query else path

        lines = [
            f"    def test_{index + 1:02d}_{method_name}(self):",
            '        """',
        ]

        # Add LLM comment if available
        if self.llm_comments and (index + 1) in self.llm_comments:
            lines.append(f"        {self.llm_comments[index + 1]}")
            lines.append("")

        lines.extend([
            f"        {req.method} {path}",
            f"        Expected: {resp.status} {resp.status_text or ''}",
            '        """',
            f'        url = BASE_URL + "{full_path}"',
        ])

        # Headers
        safe_headers = filter_headers(req.headers, exclude_auth=True)
        if req.body and self._is_json(req.body) and 'Content-Type' not in safe_headers:
            safe_headers['Content-Type'] = 'application/json'

        if safe_headers:
            headers_str = json.dumps(safe_headers, indent=12, ensure_ascii=False)
            lines.append(f"        headers = {headers_str}")
        else:
            lines.append("        headers = {}")

        # Add auth token if needed
        if index in self.needs_auth_indices and self.token_field:
            lines.extend([
                "",
                "        # Add auth token if available",
                "        if TestSession.token:",
                "            headers['Authorization'] = f'Bearer {TestSession.token}'",
            ])

        # Body
        if req.body:
            body_dict = parse_json_body(req.body)
            if body_dict:
                body_str = json.dumps(body_dict, indent=12, ensure_ascii=False)
                lines.extend([
                    "",
                    f"        json_body = {body_str}",
                ])
                request_call = f"requests.{req.method.lower()}(url, headers=headers, json=json_body)"
            else:
                escaped_body = req.body.replace('"""', '\\"\\"\\"')
                lines.extend([
                    "",
                    f'        data = """{escaped_body}"""',
                ])
                request_call = f"requests.{req.method.lower()}(url, headers=headers, data=data)"
        else:
            request_call = f"requests.{req.method.lower()}(url, headers=headers)"

        lines.extend([
            "",
            f"        response = {request_call}",
            "",
            "        # Assertions",
            f"        assert response.status_code == {resp.status}, \\",
            f'            f"Expected {resp.status}, got {{response.status_code}}: {{response.text[:200]}}"',
        ])

        # Extract token if auth request
        if index == self.auth_index and self.token_field:
            lines.extend([
                "",
                "        # Extract auth token for subsequent requests",
                "        data = assert_json_response(response, 'Login failed: ')",
                f"        TestSession.token = data.get('{self.token_field}')",
                "        assert TestSession.token, 'Token not found in login response'",
            ])
        elif resp.body:
            resp_body = parse_json_body(resp.body)
            if resp_body and isinstance(resp_body, dict):
                keys = list(resp_body.keys())[:5]
                lines.extend([
                    "",
                    "        # Verify response structure",
                    "        data = assert_json_response(response)",
                ])
                for key in keys:
                    lines.append(f'        assert "{key}" in data, "Missing key: {key}"')

        lines.extend(["", ""])
        return lines

    def _generate_main_block(self) -> list[str]:
        """Generate __main__ block for direct execution."""
        return [
            "",
            "# =============================================================================",
            "# Direct execution support",
            "# =============================================================================",
            "",
            'if __name__ == "__main__":',
            '    exit_code = pytest.main([__file__, "-v", "--tb=short"])',
            "    sys.exit(exit_code)",
            "",
        ]

    def _empty_template(self) -> str:
        """Return template for empty session."""
        return '''"""
Auto-generated pytest tests from ErrorLens session.
No requests were recorded.
"""

import pytest


def test_placeholder():
    """No requests recorded in this session."""
    pytest.skip("No requests to test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    def _is_json(self, text: str) -> bool:
        """Check if text is valid JSON."""
        return parse_json_body(text) is not None


# =============================================================================
# Public API (backward compatible)
# =============================================================================

def generate_pytest_file(
    recorded_requests: list[RecordedHttpExchange],
    test_name: str = "test_session",
    base_url_variable: bool = True,
    llm_comments: dict[int, str] | None = None,
) -> str:
    """Generate a runnable pytest file from recorded requests."""
    generator = PytestGenerator(
        recorded_requests=recorded_requests,
        test_name=test_name,
        llm_comments=llm_comments,
    )
    return generator.generate()


async def generate_pytest_file_async(
    recorded_requests: list[RecordedHttpExchange],
    test_name: str = "test_session",
    base_url_variable: bool = True,
    use_llm: bool = True,
) -> str:
    """Generate pytest file with optional LLM-powered comments."""
    llm_comments = {}

    if use_llm and recorded_requests:
        try:
            llm_comments = await generate_llm_comments(recorded_requests)
            logger.info(f"Generated LLM comments for {len(llm_comments)} requests")
        except Exception as e:
            logger.warning(f"Failed to generate LLM comments: {e}")

    return generate_pytest_file(
        recorded_requests=recorded_requests,
        test_name=test_name,
        base_url_variable=base_url_variable,
        llm_comments=llm_comments,
    )
