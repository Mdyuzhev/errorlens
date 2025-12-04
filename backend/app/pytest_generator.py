"""Generate pytest test files from recorded HTTP sessions.

This module generates clean, well-documented pytest test files with:
- Intelligent token extraction and sharing between tests
- LLM-powered comments explaining business logic
- Beautiful result summary with pass/fail statistics
"""

import json
import logging
from urllib.parse import urlparse

from app.models_pydantic import RecordedHttpExchange
from app.config import settings
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider

logger = logging.getLogger(__name__)

# Token field names commonly found in auth responses
TOKEN_FIELDS = ['token', 'access_token', 'accessToken', 'jwt', 'auth_token', 'authToken', 'id_token']
# Auth endpoint patterns
AUTH_PATTERNS = ['login', 'auth', 'signin', 'sign-in', 'authenticate', 'token', 'oauth']


def _get_llm_provider() -> LLMProvider | None:
    """Get LLM provider if configured, None otherwise."""
    try:
        if settings.llm_provider == "groq" and settings.groq_api_key:
            return GroqProvider()
        if settings.gemini_api_key:
            return GeminiProvider()
        if settings.groq_api_key:
            return GroqProvider()
    except Exception as e:
        logger.warning(f"Could not initialize LLM provider: {e}")
    return None


async def _generate_llm_comments(recorded_requests: list[RecordedHttpExchange]) -> dict[int, str]:
    """Ask LLM to generate intelligent comments for each request.

    Returns dict mapping request index to comment string.
    """
    provider = _get_llm_provider()
    if not provider:
        logger.info("No LLM provider configured, skipping intelligent comments")
        return {}

    # Build context for LLM
    requests_summary = []
    for i, exchange in enumerate(recorded_requests):
        req = exchange.request
        resp = exchange.response
        path = urlparse(req.url).path or "/"

        body_preview = ""
        if req.body:
            try:
                body_dict = json.loads(req.body)
                body_preview = f", body keys: {list(body_dict.keys())[:5]}"
            except:
                body_preview = ", body: form-data"

        resp_preview = ""
        if resp.body:
            try:
                resp_dict = json.loads(resp.body)
                if isinstance(resp_dict, dict):
                    resp_preview = f", response keys: {list(resp_dict.keys())[:5]}"
            except:
                pass

        requests_summary.append(
            f"{i+1}. {req.method} {path} -> {resp.status}{body_preview}{resp_preview}"
        )

    prompt = f"""You are a QA engineer writing pytest test comments.

Given this API session flow:
{chr(10).join(requests_summary)}

For EACH request, write a SHORT (1-2 sentences) comment explaining:
- What this request does in business terms
- Why it matters in the test flow

Return JSON object with request numbers as keys:
{{
    "1": "Login request - authenticates user and retrieves JWT token for subsequent API calls",
    "2": "Fetch products list - verifies catalog is accessible after authentication",
    ...
}}

Be concise and professional. Focus on WHAT and WHY, not HOW."""

    try:
        raw_response = await provider.analyze(prompt)

        # Parse response
        text = raw_response.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        comments_dict = json.loads(text)
        # Convert string keys to int
        return {int(k): v for k, v in comments_dict.items()}
    except Exception as e:
        logger.warning(f"Failed to generate LLM comments: {e}")
        return {}


def _detect_auth_request(exchange: RecordedHttpExchange) -> tuple[bool, str | None]:
    """Detect if request is authentication and which field contains token.

    Returns (is_auth, token_field_name).
    """
    req = exchange.request
    resp = exchange.response
    path = urlparse(req.url).path.lower()

    # Check if URL matches auth patterns
    is_auth_endpoint = any(pattern in path for pattern in AUTH_PATTERNS)

    if not is_auth_endpoint or resp.status != 200:
        return False, None

    # Try to find token in response
    if resp.body:
        try:
            resp_body = json.loads(resp.body)
            if isinstance(resp_body, dict):
                for field in TOKEN_FIELDS:
                    if field in resp_body:
                        return True, field
        except:
            pass

    return is_auth_endpoint, None


def _detect_requests_needing_auth(recorded_requests: list[RecordedHttpExchange], auth_index: int) -> set[int]:
    """Detect which requests after auth likely need token.

    Simple heuristic: API requests after login that aren't public.
    """
    needs_auth = set()

    for i, exchange in enumerate(recorded_requests):
        if i <= auth_index:
            continue

        path = urlparse(exchange.request.url).path.lower()
        # Skip obvious public endpoints
        public_patterns = ['health', 'ping', 'status', 'public', 'version']
        if any(p in path for p in public_patterns):
            continue

        # API endpoints likely need auth
        if '/api/' in path or exchange.request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            needs_auth.add(i)

    return needs_auth


def generate_pytest_file(
    recorded_requests: list[RecordedHttpExchange],
    test_name: str = "test_session",
    base_url_variable: bool = True,
    llm_comments: dict[int, str] | None = None,
) -> str:
    """Generate a runnable pytest file from recorded requests.

    Args:
        recorded_requests: List of HTTP exchanges to convert
        test_name: Name for test file/class
        base_url_variable: Whether to extract base URL as variable
        llm_comments: Optional dict of LLM-generated comments per request index
    """
    if not recorded_requests:
        return _empty_test_template(test_name)

    # Detect auth request and token handling
    auth_index = -1
    token_field = None
    for i, exchange in enumerate(recorded_requests):
        is_auth, field = _detect_auth_request(exchange)
        if is_auth and field:
            auth_index = i
            token_field = field
            break

    needs_auth_indices = set()
    if auth_index >= 0:
        needs_auth_indices = _detect_requests_needing_auth(recorded_requests, auth_index)

    # Extract base URL from first request
    first_url = recorded_requests[0].request.url
    parsed = urlparse(first_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Build test file with rich documentation
    lines = [
        '"""',
        "Auto-generated pytest tests from ErrorLens session.",
        "",
        "This file contains API tests automatically generated from recorded browser session.",
        "Tests are designed to run sequentially and share state (like auth tokens).",
        "",
        f"Run with: pytest {test_name}.py -v",
        f"Or simply: python {test_name}.py",
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
        "# Base URL - override with environment variable or change here",
        f'BASE_URL = os.environ.get("BASE_URL", "{base_url}")',
        "",
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
        "        # Any response means server is up (even 404)",
        "    except requests.exceptions.ConnectionError:",
        "        pytest.exit(",
        f'            f"API server unavailable at {{BASE_URL}}. '
        'Start the server or set BASE_URL env variable.",',
        "            returncode=1",
        "        )",
        "    except requests.exceptions.Timeout:",
        "        pytest.exit(",
        f'            f"API server timeout at {{BASE_URL}}. Server may be overloaded.",',
        "            returncode=1",
        "        )",
        "",
        "",
        "# =============================================================================",
        "# Helper Functions",
        "# =============================================================================",
        "",
        "def assert_json_response(response, context=''):",
        '    """Assert response is JSON and return parsed data."""',
        "    content_type = response.headers.get('Content-Type', '')",
        "    if 'application/json' not in content_type:",
        "        # Check for common error pages",
        "        text = response.text[:500]",
        "        if '<!DOCTYPE' in text or '<html' in text:",
        "            pytest.fail(",
        "                f\"{context}Server returned HTML instead of JSON. \"",
        "                f\"Possible causes: wrong URL, API not running, or server misconfiguration.\\n\"",
        "                f\"Status: {response.status_code}, Content-Type: {content_type}\"",
        "            )",
        "        pytest.fail(",
        "            f\"{context}Expected JSON response, got {content_type}: {text[:200]}\"",
        "        )",
        "    return response.json()",
        "",
        "",
        "# =============================================================================",
        "# Test Class",
        "# =============================================================================",
        "",
        "class TestSession:",
        '    """',
        "    Tests generated from recorded browser session.",
        "    ",
        "    Tests run in order and share authentication state.",
        "    Override BASE_URL with environment variable for different environments.",
        '    """',
        "",
    ]

    # Add token class variable if auth detected
    if auth_index >= 0 and token_field:
        lines.append("    # Shared auth token extracted from login response")
        lines.append("    token = None")
        lines.append("")

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

        # Add LLM comment if available
        if llm_comments and (i + 1) in llm_comments:
            lines.append(f"        {llm_comments[i + 1]}")
            lines.append("        ")

        lines.append(f"        {req.method} {path}")
        lines.append(f"        Expected: {resp.status} {resp.status_text or ''}")
        lines.append('        """')

        # Build request URL
        lines.append(f'        url = BASE_URL + "{full_path}"')

        # Headers (filter out sensitive ones)
        safe_headers = _filter_headers(req.headers)

        # Add Content-Type if we have JSON body
        content_type_needed = req.body and _is_json(req.body) and 'Content-Type' not in safe_headers
        if content_type_needed:
            safe_headers['Content-Type'] = 'application/json'

        if safe_headers:
            headers_str = json.dumps(safe_headers, indent=12, ensure_ascii=False)
            lines.append(f"        headers = {headers_str}")
        else:
            lines.append("        headers = {}")

        # Add auth token if this request needs it
        if i in needs_auth_indices and token_field:
            lines.append("")
            lines.append("        # Add auth token if available")
            lines.append("        if TestSession.token:")
            lines.append("            headers['Authorization'] = f'Bearer {TestSession.token}'")

        # Body
        if req.body:
            try:
                body_dict = json.loads(req.body)
                body_str = json.dumps(body_dict, indent=12, ensure_ascii=False)
                lines.append("")
                lines.append(f"        json_body = {body_str}")
                request_call = f"requests.{req.method.lower()}(url, headers=headers, json=json_body)"
            except (json.JSONDecodeError, TypeError):
                # Not JSON, use as raw data
                escaped_body = req.body.replace('"""', '\\"\\"\\"')
                lines.append("")
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

        # Extract token if this is auth request
        if i == auth_index and token_field:
            lines.append("")
            lines.append("        # Extract auth token for subsequent requests")
            lines.append("        data = assert_json_response(response, 'Login failed: ')")
            lines.append(f"        TestSession.token = data.get('{token_field}')")
            lines.append("        assert TestSession.token, 'Token not found in login response'")

        # Check response body structure if JSON
        elif resp.body:
            try:
                resp_body = json.loads(resp.body)
                if isinstance(resp_body, dict) and resp_body:
                    keys = list(resp_body.keys())[:5]  # First 5 keys
                    lines.append("")
                    lines.append("        # Verify response structure")
                    lines.append("        data = assert_json_response(response)")
                    for key in keys:
                        lines.append(f'        assert "{key}" in data, "Missing key: {key}"')
            except (json.JSONDecodeError, TypeError):
                pass

        lines.append("")
        lines.append("")

    # Add main block with ResultCollector for beautiful output
    lines.extend([
        "",
        "# =============================================================================",
        "# Direct execution support with beautiful reporting",
        "# =============================================================================",
        "",
        'if __name__ == "__main__":',
        "    import time",
        "    from datetime import datetime",
        "",
        "    class DetailedResultCollector:",
        '        """Collects detailed test results for human-readable reporting."""',
        "",
        "        def __init__(self):",
        "            self.results = []",
        "            self.start_time = None",
        "",
        "        def pytest_sessionstart(self, session):",
        "            self.start_time = time.time()",
        "",
        "        def pytest_runtest_logreport(self, report):",
        '            if report.when == "call":',
        "                self.results.append({",
        "                    'name': report.nodeid.split('::')[-1],",
        "                    'status': 'PASS' if report.passed else 'FAIL',",
        "                    'duration': report.duration,",
        "                    'message': str(report.longrepr) if report.failed else None",
        "                })",
        '            elif report.when == "setup" and report.failed:',
        "                self.results.append({",
        "                    'name': report.nodeid.split('::')[-1],",
        "                    'status': 'ERROR',",
        "                    'duration': 0,",
        "                    'message': str(report.longrepr)",
        "                })",
        "",
        "        def get_summary(self):",
        "            passed = sum(1 for r in self.results if r['status'] == 'PASS')",
        "            failed = sum(1 for r in self.results if r['status'] == 'FAIL')",
        "            errors = sum(1 for r in self.results if r['status'] == 'ERROR')",
        "            total_time = time.time() - self.start_time if self.start_time else 0",
        "            return {'passed': passed, 'failed': failed, 'errors': errors, 'duration': total_time}",
        "",
        "",
        "    def print_beautiful_report(collector):",
        '        """Print human-readable test report."""',
        "        summary = collector.get_summary()",
        "        total = summary['passed'] + summary['failed'] + summary['errors']",
        "",
        "        # Header",
        '        print("\\n")',
        '        print("=" * 70)',
        '        print("                    TEST RESULTS REPORT")',
        f'        print(f"                    {{datetime.now().strftime(\\"%Y-%m-%d %H:%M:%S\\")}}")',
        '        print("=" * 70)',
        "",
        "        # Individual results",
        '        print("\\nTEST DETAILS:")',
        '        print("-" * 70)',
        "",
        "        for r in collector.results:",
        "            status_icon = {",
        "                'PASS': '[PASS]',",
        "                'FAIL': '[FAIL]',",
        "                'ERROR': '[ERR ]'",
        "            }.get(r['status'], '[????]')",
        "",
        "            # Clean test name for display",
        "            name = r['name'].replace('test_', '').replace('_', ' ').title()",
        "            print(f\"  {status_icon} {name} ({r['duration']:.2f}s)\")",
        "",
        "            if r['message']:",
        "                # Extract first meaningful line of error",
        "                error_lines = str(r['message']).split('\\n')",
        "                for line in error_lines:",
        "                    if 'AssertionError' in line or 'Failed:' in line or 'Error:' in line:",
        "                        clean_error = line.strip()[:60]",
        "                        print(f\"         -> {clean_error}\")",
        "                        break",
        "",
        "        # Summary",
        '        print("\\n" + "-" * 70)',
        '        print("SUMMARY:")',
        "        print(f\"  Total tests: {total}\")",
        "        print(f\"  Passed:      {summary['passed']} ({100*summary['passed']//max(total,1)}%)\")",
        "        print(f\"  Failed:      {summary['failed']}\")",
        "        print(f\"  Errors:      {summary['errors']}\")",
        "        print(f\"  Duration:    {summary['duration']:.2f}s\")",
        "",
        "        # Verdict",
        '        print("\\n" + "=" * 70)',
        "        if summary['failed'] == 0 and summary['errors'] == 0:",
        '            print("  ALL TESTS PASSED! API is working correctly.")',
        "        elif summary['passed'] > 0 and summary['failed'] > 0:",
        "            print(f\"  PARTIAL SUCCESS: {summary['passed']} passed, {summary['failed']} need attention.\")",
        "        else:",
        '            print("  TESTS FAILED: Check the errors above and fix the issues.")',
        '        print("=" * 70)',
        "",
        "",
        "    # Run tests",
        "    collector = DetailedResultCollector()",
        '    exit_code = pytest.main([__file__, "-v", "--tb=line", "-q"], plugins=[collector])',
        "",
        "    # Print beautiful report",
        "    print_beautiful_report(collector)",
        "",
        "    sys.exit(exit_code)",
        "",
    ])

    return "\n".join(lines)


async def generate_pytest_file_async(
    recorded_requests: list[RecordedHttpExchange],
    test_name: str = "test_session",
    base_url_variable: bool = True,
    use_llm: bool = True,
) -> str:
    """Generate pytest file with optional LLM-powered comments.

    This is the async version that can call LLM for intelligent comments.
    """
    llm_comments = {}

    if use_llm and recorded_requests:
        try:
            llm_comments = await _generate_llm_comments(recorded_requests)
            logger.info(f"Generated LLM comments for {len(llm_comments)} requests")
        except Exception as e:
            logger.warning(f"Failed to generate LLM comments: {e}")

    return generate_pytest_file(
        recorded_requests=recorded_requests,
        test_name=test_name,
        base_url_variable=base_url_variable,
        llm_comments=llm_comments,
    )


def _is_json(text: str) -> bool:
    """Check if text is valid JSON."""
    try:
        json.loads(text)
        return True
    except:
        return False


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
