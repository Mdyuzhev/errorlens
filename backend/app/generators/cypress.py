"""Generate Cypress API test files from recorded HTTP sessions."""

import json
from urllib.parse import urlparse

from app.models_pydantic import RecordedHttpExchange
from .base import (
    BaseGenerator,
    is_auth_endpoint,
    has_auth_header_in_request,
    filter_headers,
    extract_path,
    parse_json_body,
    escape_string,
    generate_method_name,
)


class CypressGenerator(BaseGenerator):
    """Generate Cypress API test files from recorded HTTP sessions."""

    def __init__(
        self,
        recorded_requests: list[RecordedHttpExchange],
        spec_name: str = "api_session",
        use_typescript: bool = False,
    ):
        super().__init__(recorded_requests)
        self.spec_name = spec_name
        self.use_typescript = use_typescript

    def get_file_extension(self) -> str:
        return ".cy.ts" if self.use_typescript else ".cy.js"

    def get_language(self) -> str:
        return "typescript" if self.use_typescript else "javascript"

    def generate(self) -> str:
        """Generate Cypress test file."""
        if not self.requests:
            return self._empty_template()

        lines = self._generate_header()
        lines.extend(self._generate_describe_block())

        return '\n'.join(lines)

    def _generate_header(self) -> list[str]:
        """Generate file header."""
        lines = [
            "/**",
            " * Auto-generated Cypress API tests from ErrorLens session.",
            f" * Base URL: {self.base_url}",
            " *",
            " * Run with: npx cypress run --spec cypress/e2e/{}.cy.{}".format(
                self.spec_name, "ts" if self.use_typescript else "js"
            ),
            " */",
            "",
        ]

        if self.use_typescript:
            lines.append("/// <reference types=\"cypress\" />")
            lines.append("")

        return lines

    def _generate_describe_block(self) -> list[str]:
        """Generate main describe block with tests."""
        lines = [
            f"describe('API Session Tests', () => {{",
            f"  const baseUrl = Cypress.env('API_URL') || '{self.base_url}';",
            "",
        ]

        # Add token variable if auth flow detected
        if self.has_auth_flow:
            if self.use_typescript:
                lines.append("  let authToken: string;")
            else:
                lines.append("  let authToken;")
            lines.append("")

        # Generate test cases
        for i, exchange in enumerate(self.requests):
            lines.extend(self._generate_test_case(i, exchange))

        lines.append("});")
        lines.append("")

        return lines

    def _generate_test_case(self, index: int, exchange: RecordedHttpExchange) -> list[str]:
        """Generate a single test case."""
        req = exchange.request
        resp = exchange.response
        path = extract_path(req.url)
        is_auth = is_auth_endpoint(req.url)
        needs_auth = self.has_auth_flow and not is_auth and has_auth_header_in_request(req.headers)

        # Generate test name
        method_name = generate_method_name(req.method, req.url, index)
        test_name = f"{req.method} {path}"

        lines = [
            f"  it('{test_name}', () => {{",
        ]

        # Build request options
        lines.append(f"    cy.request({{")
        lines.append(f"      method: '{req.method}',")
        lines.append(f"      url: `${{baseUrl}}{path}`,")

        # Headers
        safe_headers = filter_headers(req.headers, exclude_auth=needs_auth)
        if needs_auth or safe_headers:
            lines.append("      headers: {")
            if needs_auth:
                lines.append("        Authorization: `Bearer ${authToken}`,")
            for key, value in safe_headers.items():
                escaped_value = escape_string(value, quote_char="'")
                lines.append(f"        '{key}': '{escaped_value}',")
            lines.append("      },")

        # Body
        if req.body:
            body_dict = parse_json_body(req.body)
            if body_dict:
                body_json = json.dumps(body_dict, indent=8, ensure_ascii=False)
                lines.append(f"      body: {body_json},")
            else:
                escaped_body = escape_string(req.body, quote_char="'")
                lines.append(f"      body: '{escaped_body}',")

        lines.append(f"      failOnStatusCode: false,")
        lines.append(f"    }}).then((response) => {{")

        # Assertions
        lines.append(f"      expect(response.status).to.eq({resp.status});")

        # Extract token if auth request
        if is_auth and self.has_auth_flow:
            lines.extend([
                "",
                "      // Extract auth token for subsequent requests",
                "      authToken = response.body.token || response.body.access_token;",
                "      expect(authToken).to.exist;",
            ])
        else:
            # Response body assertions
            resp_body = parse_json_body(resp.body)
            if resp_body and isinstance(resp_body, dict):
                for key in list(resp_body.keys())[:3]:
                    lines.append(f"      expect(response.body).to.have.property('{key}');")

        lines.extend([
            "    });",
            "  });",
            "",
        ])

        return lines

    def _empty_template(self) -> str:
        """Return template for empty session."""
        ext = "ts" if self.use_typescript else "js"
        ts_ref = '/// <reference types="cypress" />\n\n' if self.use_typescript else ""
        return f"""{ts_ref}/**
 * Auto-generated Cypress API tests from ErrorLens session.
 * No requests were recorded.
 */

describe('API Session Tests', () => {{
  it.skip('No requests recorded', () => {{
    // No requests to test
  }});
}});
"""


def generate_cypress_config() -> str:
    """Generate Cypress configuration file."""
    return """{
  "e2e": {
    "baseUrl": "http://localhost:3000",
    "supportFile": false,
    "specPattern": "cypress/e2e/**/*.cy.{js,ts}",
    "env": {
      "API_URL": "http://localhost:8000"
    }
  }
}
"""


def generate_package_json_deps() -> dict:
    """Return npm dependencies needed for Cypress tests."""
    return {
        "devDependencies": {
            "cypress": "^13.6.0",
            "typescript": "^5.3.0"
        },
        "scripts": {
            "cypress:open": "cypress open",
            "cypress:run": "cypress run",
            "test:api": "cypress run --spec 'cypress/e2e/**/*.cy.js'"
        }
    }


# =============================================================================
# Public API
# =============================================================================

def generate_cypress_file(
    recorded_requests: list[RecordedHttpExchange],
    spec_name: str = "api_session",
    use_typescript: bool = False,
) -> str:
    """Generate a Cypress test file from recorded requests."""
    generator = CypressGenerator(
        recorded_requests=recorded_requests,
        spec_name=spec_name,
        use_typescript=use_typescript,
    )
    return generator.generate()
