"""Generate pytest test files from recorded HTTP sessions."""

import json
from urllib.parse import urlparse

from app.models_pydantic import RecordedHttpExchange


def generate_pytest_file(
    recorded_requests: list[RecordedHttpExchange],
    test_name: str = "test_session",
    base_url_variable: bool = True,
) -> str:
    """Generate a runnable pytest file from recorded requests."""
    if not recorded_requests:
        return _empty_test_template(test_name)

    # Extract base URL from first request
    first_url = recorded_requests[0].request.url
    parsed = urlparse(first_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Build test file
    lines = [
        '"""',
        "Auto-generated pytest tests from ErrorLens session.",
        f"Run with: pytest {test_name}.py -v",
        f"Or simply: python {test_name}.py",
        '"""',
        "",
        "import requests",
        "import pytest",
        "",
        "# Base URL - change this for different environments",
        f'BASE_URL = "{base_url}"',
        "",
        "",
        "class TestSession:",
        '    """Tests generated from recorded browser session."""',
        "",
    ]

    for i, exchange in enumerate(recorded_requests):
        req = exchange.request
        resp = exchange.response

        # Generate test method
        method_name = _generate_method_name(req.method, req.url, i)
        path = urlparse(req.url).path or "/"
        query = urlparse(req.url).query

        # Include query string in path if present
        full_path = f"{path}?{query}" if query else path

        lines.append(f"    def test_{i + 1:02d}_{method_name}(self):")
        lines.append('        """')
        lines.append(f"        {req.method} {path}")
        lines.append(f"        Expected: {resp.status} {resp.status_text or ''}")
        lines.append('        """')

        # Build request
        lines.append(f'        url = BASE_URL + "{full_path}"')

        # Headers (filter out sensitive ones)
        safe_headers = _filter_headers(req.headers)
        if safe_headers:
            headers_str = json.dumps(safe_headers, indent=12, ensure_ascii=False)
            lines.append(f"        headers = {headers_str}")
        else:
            lines.append("        headers = {}")

        # Body
        if req.body:
            try:
                body_dict = json.loads(req.body)
                body_str = json.dumps(body_dict, indent=12, ensure_ascii=False)
                lines.append(f"        json_body = {body_str}")
                request_call = f"requests.{req.method.lower()}(url, headers=headers, json=json_body)"
            except (json.JSONDecodeError, TypeError):
                # Not JSON, use as raw data
                escaped_body = req.body.replace('"""', '\\"\\"\\"')
                lines.append(f'        data = """{escaped_body}"""')
                request_call = f"requests.{req.method.lower()}(url, headers=headers, data=data)"
        else:
            request_call = f"requests.{req.method.lower()}(url, headers=headers)"

        lines.append("")
        lines.append(f"        response = {request_call}")
        lines.append("")

        # Assertions
        lines.append("        # Assertions")
        lines.append(f"        assert response.status_code == {resp.status}, \\")
        lines.append(
            f'            f"Expected {resp.status}, got {{response.status_code}}: {{response.text[:200]}}"'
        )

        # Check response body structure if JSON
        if resp.body:
            try:
                resp_body = json.loads(resp.body)
                if isinstance(resp_body, dict) and resp_body:
                    keys = list(resp_body.keys())[:5]  # First 5 keys
                    lines.append("")
                    lines.append("        # Verify response structure")
                    lines.append("        data = response.json()")
                    for key in keys:
                        lines.append(f'        assert "{key}" in data, "Missing key: {key}"')
            except (json.JSONDecodeError, TypeError):
                pass

        lines.append("")
        lines.append("")

    # Add main block for direct execution
    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append("    # Run with: python this_file.py")
    lines.append('    pytest.main([__file__, "-v", "--tb=short"])')
    lines.append("")

    return "\n".join(lines)


def _generate_method_name(method: str, url: str, index: int) -> str:
    """Generate readable method name from URL."""
    path = urlparse(url).path or "/"
    # Clean path: /api/users/123 -> api_users
    parts = [p for p in path.split("/") if p and not p.isdigit()][-2:]
    if parts:
        name = "_".join(parts).replace("-", "_").replace(".", "_")
        # Sanitize: only allow alphanumeric and underscore
        name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return f"{method.lower()}_{name}"
    return f"{method.lower()}_request"


def _filter_headers(headers: dict) -> dict:
    """Remove sensitive headers."""
    skip = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "x-admin-key",
        "set-cookie",
    }
    return {k: v for k, v in headers.items() if k.lower() not in skip}


def _empty_test_template(test_name: str) -> str:
    """Return template for empty session."""
    return f'''"""
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
