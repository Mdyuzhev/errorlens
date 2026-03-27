"""Static test generator and renderers — port of Pe4King generator.ts + renderers."""

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.generators.spec_parser import EndpointInfo, SchemaField, ParameterInfo


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GeneratorConfig:
    base_url: str = ""
    framework: str = "pytest"       # pytest | rest-assured | postman
    generate_negative_tests: bool = True
    use_placeholders: bool = True
    java_package: str = "com.api.tests"


@dataclass
class GeneratedFile:
    filename: str
    content: str
    language: str   # python, java, json


@dataclass
class GenerationStats:
    total_endpoints: int = 0
    total_tests: int = 0
    positive_tests: int = 0
    negative_tests: int = 0
    assertions: int = 0


@dataclass
class GenerationResult:
    success: bool
    files: list[GeneratedFile]
    stats: GenerationStats
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_sample(f: SchemaField) -> Any:
    """Generate a sample value based on field schema."""
    if f.example is not None:
        return f.example
    if f.enum_values:
        return f.enum_values[0]

    t = f.field_type
    if t == "string":
        fmt = f.format or ""
        if fmt == "email":
            return "test@example.com"
        if fmt == "uuid":
            return "550e8400-e29b-41d4-a716-446655440000"
        if fmt == "date-time":
            return "2024-01-01T00:00:00Z"
        if fmt == "uri":
            return "https://example.com"
        return "test_string"
    if t == "integer":
        if f.minimum is not None:
            return int(f.minimum)
        if f.maximum is not None:
            return int(f.maximum)
        return 1
    if t == "number":
        if f.minimum is not None:
            return f.minimum
        if f.maximum is not None:
            return f.maximum
        return 1.0
    if t == "boolean":
        return True
    if t == "array":
        return []
    if t == "object":
        return {}
    return None


def _build_body(fields: list[SchemaField], config: GeneratorConfig) -> dict:
    """Build request body dict from top-level required fields."""
    body: dict[str, Any] = {}
    for f in fields:
        if "." in f.path:
            continue
        if f.required:
            body[f.name] = _generate_sample(f)
    return body


def _build_assertions(endpoint: EndpointInfo) -> list[str]:
    """Build pytest assertion strings for response fields."""
    assertions: list[str] = []
    for f in endpoint.response_fields:
        name = f.name
        if f.enum_values:
            assertions.append(
                f'assert data["{name}"] in {f.enum_values}'
            )
        elif f.format == "uuid":
            assertions.append(
                f'assert re.match('
                f'r"^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$", '
                f'data["{name}"])'
            )
        elif f.format == "email":
            assertions.append(f'assert "@" in data["{name}"]')
        elif f.format == "date-time" or name.endswith("_at") or name.endswith("_time"):
            assertions.append(
                f'assert re.match(r"^\\d{{4}}-\\d{{2}}-\\d{{2}}", data["{name}"])'
            )
        else:
            added = False
            if f.minimum is not None:
                assertions.append(f'assert data["{name}"] >= {f.minimum}')
                added = True
            if f.maximum is not None:
                assertions.append(f'assert data["{name}"] <= {f.maximum}')
                added = True
            if f.min_length is not None:
                assertions.append(f'assert len(data["{name}"]) >= {f.min_length}')
                added = True
            if not added:
                assertions.append(f'assert data["{name}"] is not None')
    return assertions


def _sanitize_path(path: str) -> str:
    """Convert /users/{id}/pets to users_by_id_pets."""
    s = path.strip("/")
    s = re.sub(r"\{(\w+)\}", r"by_\1", s)
    s = s.replace("/", "_").replace("-", "_")
    return s


def _method_path_for_request(
    path: str, endpoint: EndpointInfo, config: GeneratorConfig,
) -> str:
    """Return the path string for use in generated code."""
    result = path
    for pp in endpoint.path_params:
        placeholder = "{" + pp.name + "}"
        if config.use_placeholders:
            var = pp.name.upper() + "_ID" if not pp.name.upper().endswith("_ID") else pp.name.upper()
            result = result.replace(placeholder, f"{{{var}}}")
        else:
            sample = _generate_sample(pp.schema)
            result = result.replace(placeholder, str(sample))
    return result


# ---------------------------------------------------------------------------
# Pytest renderer
# ---------------------------------------------------------------------------

class SpecPytestRenderer:
    def render(
        self, endpoints: list[EndpointInfo], config: GeneratorConfig,
    ) -> list[GeneratedFile]:
        base = config.base_url or "http://localhost:8000"
        conftest = self._render_conftest(base)
        test_file = self._render_tests(endpoints, config)
        reqs = "pytest>=7.0.0\nrequests>=2.28.0\n"
        return [
            GeneratedFile(filename="test_api.py", content=test_file, language="python"),
            GeneratedFile(filename="conftest.py", content=conftest, language="python"),
            GeneratedFile(filename="requirements.txt", content=reqs, language="text"),
        ]

    def _render_conftest(self, base_url: str) -> str:
        return (
            'import pytest\n'
            'import requests\n'
            '\n'
            f'BASE_URL = "{base_url}"\n'
            '\n'
            '\n'
            'class ApiClient:\n'
            '    def __init__(self):\n'
            '        self.session = requests.Session()\n'
            '        self.base_url = BASE_URL\n'
            '\n'
            '    def get(self, path, **kwargs):\n'
            '        return self.session.get(f"{self.base_url}{path}", **kwargs)\n'
            '\n'
            '    def post(self, path, **kwargs):\n'
            '        return self.session.post(f"{self.base_url}{path}", **kwargs)\n'
            '\n'
            '    def put(self, path, **kwargs):\n'
            '        return self.session.put(f"{self.base_url}{path}", **kwargs)\n'
            '\n'
            '    def patch(self, path, **kwargs):\n'
            '        return self.session.patch(f"{self.base_url}{path}", **kwargs)\n'
            '\n'
            '    def delete(self, path, **kwargs):\n'
            '        return self.session.delete(f"{self.base_url}{path}", **kwargs)\n'
            '\n'
            '\n'
            '@pytest.fixture\n'
            'def api_client():\n'
            '    return ApiClient()\n'
        )

    def _render_tests(
        self, endpoints: list[EndpointInfo], config: GeneratorConfig,
    ) -> str:
        lines: list[str] = [
            "import re",
            "import pytest",
            "",
            "",
            "class TestApi:",
        ]
        for ep in endpoints:
            lines.extend(self._render_endpoint(ep, config))
        return "\n".join(lines) + "\n"

    def _render_endpoint(
        self, ep: EndpointInfo, config: GeneratorConfig,
    ) -> list[str]:
        lines: list[str] = []
        method = ep.method.lower()
        sanitized = _sanitize_path(ep.path)
        func_name = f"test_{method}_{sanitized}"

        request_path = _method_path_for_request(ep.path, ep, config)

        # --- positive test ---
        lines.append("")
        lines.append(f'    def {func_name}(self, api_client):')
        lines.append(f'        """{ep.method} {ep.path}"""')
        lines.append("        # Arrange")

        has_body = method in ("post", "put", "patch") and ep.request_body_schema
        has_query = bool(ep.query_params)

        if has_query:
            q_parts: list[str] = []
            for qp in ep.query_params:
                val = _generate_sample(qp.schema)
                q_parts.append(f'"{qp.name}": {repr(val)}')
            lines.append("        params = {" + ", ".join(q_parts) + "}")

        if has_body:
            body = _build_body(ep.request_body_schema, config)
            lines.append(f"        body = {repr(body)}")

        lines.append("        # Act")
        call_args: list[str] = [f'"{request_path}"']
        if has_query:
            call_args.append("params=params")
        if has_body:
            call_args.append("json=body")
        lines.append(
            f"        response = api_client.{method}({', '.join(call_args)})"
        )

        lines.append("        # Assert")
        lines.append(f"        assert response.status_code == {ep.success_status}")

        if ep.has_response_schema and ep.response_fields:
            lines.append("        data = response.json()")
            for a in _build_assertions(ep):
                lines.append(f"        {a}")
        else:
            lines.append("        data = response.json()")
            lines.append("        assert data is not None")

        # --- negative tests ---
        if config.generate_negative_tests and has_body:
            required_fields = [
                f for f in ep.request_body_schema if f.required
            ]
            # Missing required fields
            for rf in required_fields:
                neg_name = f"{func_name}_missing_{rf.name}"
                lines.append("")
                lines.append("    @pytest.mark.negative")
                lines.append(f"    def {neg_name}(self, api_client):")
                lines.append(
                    f'        """{ep.method} {ep.path}'
                    f' — Missing required field: {rf.name}"""'
                )
                body_without = {
                    k: v
                    for k, v in _build_body(ep.request_body_schema, config).items()
                    if k != rf.name
                }
                lines.append(f"        body = {repr(body_without)}")
                lines.append(
                    f"        response = api_client.{method}"
                    f'("{request_path}", json=body)'
                )
                lines.append(
                    "        assert response.status_code in [400, 422]"
                )

            # Boundary violations
            for rf in ep.request_body_schema:
                if rf.minimum is not None:
                    neg_name = f"{func_name}_invalid_{rf.name}_below_min"
                    lines.append("")
                    lines.append("    @pytest.mark.negative")
                    lines.append(f"    def {neg_name}(self, api_client):")
                    lines.append(
                        f'        """{ep.method} {ep.path}'
                        f' — {rf.name} below minimum"""'
                    )
                    body = _build_body(ep.request_body_schema, config)
                    body[rf.name] = rf.minimum - 1
                    lines.append(f"        body = {repr(body)}")
                    lines.append(
                        f"        response = api_client.{method}"
                        f'("{request_path}", json=body)'
                    )
                    lines.append(
                        "        assert response.status_code in [400, 422]"
                    )

                if rf.maximum is not None:
                    neg_name = f"{func_name}_invalid_{rf.name}_above_max"
                    lines.append("")
                    lines.append("    @pytest.mark.negative")
                    lines.append(f"    def {neg_name}(self, api_client):")
                    lines.append(
                        f'        """{ep.method} {ep.path}'
                        f' — {rf.name} above maximum"""'
                    )
                    body = _build_body(ep.request_body_schema, config)
                    body[rf.name] = rf.maximum + 1
                    lines.append(f"        body = {repr(body)}")
                    lines.append(
                        f"        response = api_client.{method}"
                        f'("{request_path}", json=body)'
                    )
                    lines.append(
                        "        assert response.status_code in [400, 422]"
                    )

        return lines


# ---------------------------------------------------------------------------
# REST Assured renderer
# ---------------------------------------------------------------------------

class SpecRestAssuredRenderer:
    def render(
        self, endpoints: list[EndpointInfo], config: GeneratorConfig,
    ) -> list[GeneratedFile]:
        base = config.base_url or "http://localhost:8000"
        pkg = config.java_package
        lines: list[str] = [
            f"package {pkg};",
            "",
            "import io.restassured.RestAssured;",
            "import io.restassured.http.ContentType;",
            "import org.junit.jupiter.api.*;",
            "import static io.restassured.RestAssured.*;",
            "import static org.hamcrest.Matchers.*;",
            "",
            "@TestMethodOrder(MethodOrderer.OrderAnnotation.class)",
            "public class ApiTests {",
            "",
            "    @BeforeAll",
            "    static void setup() {",
            f'        RestAssured.baseURI = "{base}";',
            "    }",
        ]

        for ep in endpoints:
            lines.extend(self._render_endpoint(ep, config))

        lines.append("}")
        content = "\n".join(lines) + "\n"
        return [
            GeneratedFile(
                filename="ApiTests.java", content=content, language="java",
            ),
        ]

    def _render_endpoint(
        self, ep: EndpointInfo, config: GeneratorConfig,
    ) -> list[str]:
        lines: list[str] = []
        method = ep.method.lower()
        sanitized = _sanitize_path(ep.path)
        java_name = "test" + "".join(
            w.capitalize() for w in f"{method}_{sanitized}".split("_")
        )
        display = f"{ep.method} {ep.path}"
        if ep.summary:
            display += f" - {ep.summary}"

        request_path = _method_path_for_request(ep.path, ep, config)
        has_body = method in ("post", "put", "patch") and ep.request_body_schema

        # Positive test
        lines.append("")
        lines.append("    @Test")
        lines.append(f'    @DisplayName("{display}")')
        lines.append(f"    void {java_name}() {{")
        lines.append("        given()")
        lines.append("            .contentType(ContentType.JSON)")

        if has_body:
            body = _build_body(ep.request_body_schema, config)
            body_json = json.dumps(body)
            lines.append(f'            .body("{_escape_java(body_json)}")')

        lines.append("        .when()")
        lines.append(f'            .{method}("{request_path}")')
        lines.append("        .then()")
        lines.append(f"            .statusCode({ep.success_status})")

        if ep.has_response_schema and ep.response_fields:
            for rf in ep.response_fields:
                if rf.enum_values:
                    vals = ", ".join(f'"{v}"' for v in rf.enum_values)
                    lines.append(
                        f'            .body("{rf.name}", oneOf({vals}))'
                    )
                else:
                    lines.append(
                        f'            .body("{rf.name}", notNullValue())'
                    )
        else:
            lines.append('            .body("size()", greaterThanOrEqualTo(0));')

        # Remove trailing body line's semicolon and add it properly
        if not lines[-1].endswith(";"):
            lines[-1] += ";"

        lines.append("    }")

        # Negative tests
        if config.generate_negative_tests and has_body:
            required_fields = [
                f for f in ep.request_body_schema if f.required
            ]
            for rf in required_fields:
                neg_name = java_name + "Missing" + rf.name.capitalize()
                lines.append("")
                lines.append(f"    // Negative: missing {rf.name}")
                lines.append("    @Test")
                lines.append(
                    f'    @DisplayName("{ep.method} {ep.path}'
                    f' - missing {rf.name}")'
                )
                lines.append(f"    void {neg_name}() {{")
                body_without = {
                    k: v
                    for k, v in _build_body(ep.request_body_schema, config).items()
                    if k != rf.name
                }
                body_json = json.dumps(body_without)
                lines.append("        given()")
                lines.append("            .contentType(ContentType.JSON)")
                lines.append(
                    f'            .body("{_escape_java(body_json)}")'
                )
                lines.append("        .when()")
                lines.append(f'            .{method}("{request_path}")')
                lines.append("        .then()")
                lines.append("            .statusCode(anyOf(is(400), is(422)));")
                lines.append("    }")

        return lines


def _escape_java(s: str) -> str:
    """Escape a string for Java string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ---------------------------------------------------------------------------
# Postman renderer
# ---------------------------------------------------------------------------

class SpecPostmanRenderer:
    def render(
        self, endpoints: list[EndpointInfo], config: GeneratorConfig,
    ) -> list[GeneratedFile]:
        base = config.base_url or "http://localhost:8000"
        # Group by tag
        groups: dict[str, list[EndpointInfo]] = {}
        for ep in endpoints:
            tag = ep.tags[0] if ep.tags else "Other"
            groups.setdefault(tag, []).append(ep)

        items: list[dict] = []
        for tag, eps in groups.items():
            folder_items: list[dict] = []
            for ep in eps:
                folder_items.extend(self._render_endpoint(ep, config))
            items.append({"name": tag, "item": folder_items})

        collection = {
            "info": {
                "name": "API Tests",
                "_postman_id": str(uuid.uuid4()),
                "schema": (
                    "https://schema.getpostman.com/json/collection/"
                    "v2.1.0/collection.json"
                ),
            },
            "item": items,
            "variable": [
                {"key": "base_url", "value": base, "type": "string"},
            ],
        }
        content = json.dumps(collection, indent=2)
        return [
            GeneratedFile(
                filename="collection.json", content=content, language="json",
            ),
        ]

    def _render_endpoint(
        self, ep: EndpointInfo, config: GeneratorConfig,
    ) -> list[dict]:
        items: list[dict] = []
        method = ep.method.upper()
        request_path = _method_path_for_request(ep.path, ep, config)
        path_parts = [p for p in request_path.strip("/").split("/") if p]
        display = f"{method} {ep.path}"

        has_body = method in ("POST", "PUT", "PATCH") and ep.request_body_schema

        request_obj: dict[str, Any] = {
            "method": method,
            "url": {
                "raw": "{{base_url}}" + request_path,
                "host": ["{{base_url}}"],
                "path": path_parts,
            },
            "header": [
                {"key": "Content-Type", "value": "application/json"},
            ],
        }
        if has_body:
            body = _build_body(ep.request_body_schema, config)
            request_obj["body"] = {
                "mode": "raw",
                "raw": json.dumps(body, indent=2),
            }

        # Test script
        test_lines = [
            f"pm.test('Status code is {ep.success_status}', function() {{",
            f"    pm.response.to.have.status({ep.success_status});",
            "});",
        ]
        if ep.has_response_schema and ep.response_fields:
            test_lines.append(
                "pm.test('Response has expected fields', function() {"
            )
            test_lines.append("    var data = pm.response.json();")
            for rf in ep.response_fields:
                test_lines.append(
                    f"    pm.expect(data.{rf.name}).to.not.be.undefined;"
                )
            test_lines.append("});")

        items.append({
            "name": display,
            "request": request_obj,
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": test_lines,
                    },
                },
            ],
        })

        # Negative tests
        if config.generate_negative_tests and has_body:
            required_fields = [
                f for f in ep.request_body_schema if f.required
            ]
            for rf in required_fields:
                neg_body = {
                    k: v
                    for k, v in _build_body(ep.request_body_schema, config).items()
                    if k != rf.name
                }
                neg_request = {
                    "method": method,
                    "url": {
                        "raw": "{{base_url}}" + request_path,
                        "host": ["{{base_url}}"],
                        "path": path_parts,
                    },
                    "header": [
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps(neg_body, indent=2),
                    },
                }
                neg_test_lines = [
                    "pm.test('Status code is 400 or 422', function() {",
                    "    pm.expect("
                    "[400, 422]).to.include(pm.response.code);",
                    "});",
                ]
                items.append({
                    "name": f"{display} - missing {rf.name}",
                    "request": neg_request,
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": neg_test_lines,
                            },
                        },
                    ],
                })

        return items


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

class SpecTestGenerator:
    def generate(
        self, endpoints: list[EndpointInfo], config: GeneratorConfig,
    ) -> GenerationResult:
        stats = GenerationStats(total_endpoints=len(endpoints))
        errors: list[str] = []

        if config.framework == "pytest":
            renderer: SpecPytestRenderer | SpecRestAssuredRenderer | SpecPostmanRenderer = SpecPytestRenderer()
        elif config.framework == "rest-assured":
            renderer = SpecRestAssuredRenderer()
        elif config.framework == "postman":
            renderer = SpecPostmanRenderer()
        else:
            return GenerationResult(
                success=False, files=[], stats=stats,
                errors=[f"Unknown framework: {config.framework}"],
            )

        try:
            files = renderer.render(endpoints, config)
            for f in files:
                if config.framework == "pytest":
                    stats.total_tests += f.content.count("def test_")
                    neg = f.content.count("@pytest.mark.negative")
                    stats.negative_tests += neg
                    stats.positive_tests += f.content.count("def test_") - neg
                    stats.assertions += f.content.count("assert ")
                elif config.framework == "rest-assured":
                    tests_count = f.content.count("@Test")
                    neg_count = f.content.count("// Negative:")
                    stats.total_tests += tests_count
                    stats.negative_tests += neg_count
                    stats.positive_tests += tests_count - neg_count
                    stats.assertions += f.content.count(".body(")
                elif config.framework == "postman":
                    try:
                        coll = json.loads(f.content)
                        items = coll.get("item", [])
                        for folder in items:
                            sub_items = folder.get("item", [])
                            stats.total_tests += len(sub_items)
                            for si in sub_items:
                                events = si.get("event", [])
                                for ev in events:
                                    if ev.get("listen") == "test":
                                        script = ev.get("script", {}).get(
                                            "exec", [],
                                        )
                                        stats.assertions += sum(
                                            1 for line in script
                                            if "pm.test" in line
                                        )
                    except (json.JSONDecodeError, TypeError):
                        pass

            stats.positive_tests = max(0, stats.positive_tests)
            stats.negative_tests = max(0, stats.negative_tests)
        except Exception as e:
            errors.append(str(e))
            return GenerationResult(
                success=False, files=[], stats=stats, errors=errors,
            )

        return GenerationResult(
            success=True, files=files, stats=stats, errors=errors,
        )
