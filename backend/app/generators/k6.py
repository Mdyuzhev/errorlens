"""Generate k6 load test scripts from recorded HTTP sessions."""

import json

from app.models_pydantic import RecordedHttpExchange

from .base import (
    BaseGenerator,
    detect_token_in_response,
    escape_string,
    extract_path,
    filter_headers,
    has_auth_header_in_request,
    is_auth_endpoint,
    parse_json_body,
)


class K6Generator(BaseGenerator):
    """Generate k6 load test scripts from recorded HTTP sessions."""

    def __init__(
        self,
        recorded_requests: list[RecordedHttpExchange],
        vus: int = 10,
        duration: str = "30s",
    ):
        super().__init__(recorded_requests)
        self.vus = vus
        self.duration = duration

    def get_file_extension(self) -> str:
        return ".js"

    def get_language(self) -> str:
        return "javascript"

    def generate(self) -> str:
        """Generate k6 test script."""
        if not self.requests:
            return self._empty_template()

        lines = self._generate_header()
        lines.extend(self._generate_options())
        lines.extend(self._generate_variables())
        lines.extend(self._generate_main_function())

        return "\n".join(lines)

    def _generate_header(self) -> list[str]:
        """Generate k6 imports and comments."""
        return [
            "/**",
            " * Auto-generated k6 load test from ErrorLens session.",
            f" * Base URL: {self.base_url}",
            " *",
            f" * Run with: k6 run {self._get_filename()} --vus {self.vus} --duration {self.duration}",
            " * Or use the options defined below.",
            " */",
            "",
            "import http from 'k6/http';",
            "import { check, sleep } from 'k6';",
            "import { Rate } from 'k6/metrics';",
            "",
            "// Custom metrics",
            "const errorRate = new Rate('errors');",
            "",
        ]

    def _get_filename(self) -> str:
        """Get suggested filename."""
        return "load_test.js"

    def _generate_options(self) -> list[str]:
        """Generate k6 options block."""
        return [
            "// Load test configuration",
            "export const options = {",
            f"    vus: {self.vus},              // virtual users",
            f"    duration: '{self.duration}',     // test duration",
            "    thresholds: {",
            "        http_req_duration: ['p(95)<500'],  // 95% requests < 500ms",
            "        errors: ['rate<0.1'],              // error rate < 10%",
            "    },",
            "};",
            "",
        ]

    def _generate_variables(self) -> list[str]:
        """Generate variables section."""
        lines = [
            "// Configuration",
            f"const BASE_URL = '{self.base_url}';",
            "",
        ]

        if self.has_auth_flow:
            lines.extend(
                [
                    "// Auth token (will be set after login)",
                    "let authToken = null;",
                    "",
                ]
            )

        return lines

    def _generate_main_function(self) -> list[str]:
        """Generate the main default function."""
        lines = [
            "export default function() {",
        ]

        for i, exchange in enumerate(self.requests):
            lines.extend(self._generate_request(i, exchange))

        lines.extend(
            [
                "",
                "    // Sleep between iterations",
                "    sleep(1);",
                "}",
                "",
            ]
        )

        return lines

    def _generate_request(self, index: int, exchange: RecordedHttpExchange) -> list[str]:
        """Generate code for a single request."""
        req = exchange.request
        resp = exchange.response
        method = req.method.upper()
        path = extract_path(req.url)

        lines = [
            "",
            f"    // Request {index + 1}: {method} {path}",
        ]

        # Build headers
        headers = filter_headers(req.headers, exclude_auth=self.has_auth_flow)

        # Check if this is an auth endpoint
        is_auth = is_auth_endpoint(req.url)
        needs_auth = has_auth_header_in_request(req.headers) and not is_auth

        # Variable name for response
        var_name = f"res{index + 1}"

        # Build request call
        if method == "GET":
            lines.extend(self._generate_get_request(var_name, path, headers, needs_auth))
        elif method in ("POST", "PUT", "PATCH"):
            lines.extend(
                self._generate_body_request(
                    var_name, method.lower(), path, req.body, headers, needs_auth
                )
            )
        elif method == "DELETE":
            lines.extend(self._generate_delete_request(var_name, path, headers, needs_auth))
        else:
            lines.extend(
                self._generate_generic_request(
                    var_name, method.lower(), path, req.body, headers, needs_auth
                )
            )

        # Add check
        lines.extend(self._generate_check(var_name, resp.status, index))

        # Extract token if auth endpoint
        if is_auth and self.has_auth_flow:
            token_field = detect_token_in_response(resp.body)
            if token_field:
                lines.extend(
                    [
                        f"    authToken = {var_name}.json('{token_field}');",
                    ]
                )

        return lines

    def _generate_get_request(
        self, var_name: str, path: str, headers: dict, needs_auth: bool
    ) -> list[str]:
        """Generate GET request."""
        headers_str = self._format_headers(headers, needs_auth)

        if headers_str:
            return [
                f"    let {var_name} = http.get(`${{BASE_URL}}{path}`, {{",
                f"        headers: {headers_str},",
                "    });",
            ]
        else:
            return [
                f"    let {var_name} = http.get(`${{BASE_URL}}{path}`);",
            ]

    def _generate_body_request(
        self, var_name: str, method: str, path: str, body: str, headers: dict, needs_auth: bool
    ) -> list[str]:
        """Generate POST/PUT/PATCH request with body."""
        headers_str = self._format_headers(headers, needs_auth)
        body_str = self._format_body(body)

        lines = [f"    let {var_name} = http.{method}(`${{BASE_URL}}{path}`,"]

        if body_str:
            lines.append(f"        {body_str},")
        else:
            lines.append("        null,")

        if headers_str:
            lines.append("        {")
            lines.append(f"            headers: {headers_str},")
            lines.append("        }")

        lines.append("    );")
        return lines

    def _generate_delete_request(
        self, var_name: str, path: str, headers: dict, needs_auth: bool
    ) -> list[str]:
        """Generate DELETE request."""
        headers_str = self._format_headers(headers, needs_auth)

        if headers_str:
            return [
                f"    let {var_name} = http.del(`${{BASE_URL}}{path}`, null, {{",
                f"        headers: {headers_str},",
                "    });",
            ]
        else:
            return [
                f"    let {var_name} = http.del(`${{BASE_URL}}{path}`);",
            ]

    def _generate_generic_request(
        self, var_name: str, method: str, path: str, body: str, headers: dict, needs_auth: bool
    ) -> list[str]:
        """Generate generic request for other methods."""
        headers_str = self._format_headers(headers, needs_auth)
        body_str = self._format_body(body)

        return [
            f"    let {var_name} = http.request('{method.upper()}', `${{BASE_URL}}{path}`, {body_str or 'null'}, {{",
            f"        headers: {headers_str or '{}'},",
            "    });",
        ]

    def _generate_check(self, var_name: str, expected_status: int, index: int) -> list[str]:
        """Generate check for response."""
        return [
            f"    check({var_name}, {{",
            f"        'status is {expected_status}': (r) => r.status === {expected_status},",
            "    }) || errorRate.add(1);",
        ]

    def _format_headers(self, headers: dict, needs_auth: bool) -> str:
        """Format headers as JS object."""
        h = dict(headers)

        if needs_auth:
            h["Authorization"] = '${authToken ? `Bearer ${authToken}` : ""}'

        if not h:
            return ""

        # Simple case: just content-type
        if len(h) == 1 and "Content-Type" in h:
            return f"{{ 'Content-Type': '{h['Content-Type']}' }}"

        # Complex case with auth
        if needs_auth:
            parts = []
            for k, v in h.items():
                if k == "Authorization":
                    parts.append("'Authorization': `Bearer ${authToken}`")
                else:
                    parts.append(f"'{k}': '{escape_string(v)}'")
            return "{ " + ", ".join(parts) + " }"

        # Regular headers
        parts = [f"'{k}': '{escape_string(v)}'" for k, v in h.items()]
        return "{ " + ", ".join(parts) + " }"

    def _format_body(self, body: str) -> str:
        """Format request body."""
        if not body:
            return ""

        # Try to parse as JSON
        parsed = parse_json_body(body)
        if parsed:
            return f"JSON.stringify({json.dumps(parsed)})"

        # Return as string
        return f"'{escape_string(body)}'"

    def _empty_template(self) -> str:
        """Return template when no requests."""
        return """/**
 * k6 load test template.
 * No requests were recorded - add your own tests below.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 10,
    duration: '30s',
};

export default function() {
    let res = http.get('https://example.com');
    check(res, { 'status is 200': (r) => r.status === 200 });
    sleep(1);
}
"""


def generate_k6_file(
    recorded_requests: list[RecordedHttpExchange],
    vus: int = 10,
    duration: str = "30s",
) -> str:
    """Generate k6 load test script from recorded requests.

    Args:
        recorded_requests: List of recorded HTTP exchanges
        vus: Number of virtual users (default: 10)
        duration: Test duration (default: "30s")

    Returns:
        Generated k6 JavaScript code as string
    """
    generator = K6Generator(
        recorded_requests=recorded_requests,
        vus=vus,
        duration=duration,
    )
    return generator.generate()
