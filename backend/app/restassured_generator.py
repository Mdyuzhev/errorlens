"""Generate REST Assured test files from recorded HTTP sessions."""

from app.models_pydantic import RecordedHttpExchange
from urllib.parse import urlparse
import json


def generate_restassured_file(
    recorded_requests: list[RecordedHttpExchange],
    class_name: str = "SessionTest",
    package_name: str = "com.errorlens.tests"
) -> str:
    """Generate a REST Assured Java test file from recorded requests."""

    if not recorded_requests:
        return _empty_test_template(class_name, package_name)

    # Extract base URL
    first_url = recorded_requests[0].request.url
    parsed = urlparse(first_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    lines = [
        f"package {package_name};",
        "",
        "import io.restassured.RestAssured;",
        "import io.restassured.http.ContentType;",
        "import io.restassured.response.Response;",
        "import org.junit.jupiter.api.*;",
        "import static io.restassured.RestAssured.*;",
        "import static org.hamcrest.Matchers.*;",
        "",
        "/**",
        " * Auto-generated REST Assured tests from ErrorLens session.",
        f" * Base URL: {base_url}",
        " */",
        f"public class {class_name} {{",
        "",
        "    @BeforeAll",
        "    public static void setup() {",
        f'        RestAssured.baseURI = "{base_url}";',
        "    }",
        "",
    ]

    for i, exchange in enumerate(recorded_requests):
        req = exchange.request
        resp = exchange.response

        method_name = _generate_method_name(req.method, req.url, i)
        path = urlparse(req.url).path or "/"

        lines.append("    @Test")
        lines.append(f'    @DisplayName("{req.method} {path}")')
        lines.append(f"    public void test{i+1:02d}_{method_name}() {{")

        # Build request chain
        lines.append("        given()")

        # Headers
        safe_headers = _filter_headers(req.headers)
        for key, value in safe_headers.items():
            escaped_value = value.replace('"', '\\"')
            lines.append(f'            .header("{key}", "{escaped_value}")')

        # Content type
        if req.content_type:
            lines.append(f'            .contentType("{req.content_type}")')

        # Body
        if req.body:
            try:
                # Try to parse as JSON for pretty formatting
                body_dict = json.loads(req.body)
                body_json = json.dumps(body_dict, ensure_ascii=False)
                escaped_body = body_json.replace('"', '\\"')
                lines.append(f'            .body("{escaped_body}")')
            except (json.JSONDecodeError, TypeError):
                escaped_body = req.body.replace('"', '\\"').replace('\n', '\\n')
                lines.append(f'            .body("{escaped_body}")')

        # Method and path
        lines.append("        .when()")
        lines.append(f'            .{req.method.lower()}("{path}")')

        # Assertions
        lines.append("        .then()")
        lines.append(f"            .statusCode({resp.status})")

        # Response body assertions
        if resp.body:
            try:
                resp_body = json.loads(resp.body)
                if isinstance(resp_body, dict):
                    # Add assertions for top-level keys
                    for key in list(resp_body.keys())[:3]:
                        lines.append(f'            .body("{key}", notNullValue())')
            except (json.JSONDecodeError, TypeError):
                pass

        lines.append("            .log().ifError();")
        lines.append("    }")
        lines.append("")

    lines.append("}")
    lines.append("")

    return '\n'.join(lines)


def _generate_method_name(method: str, url: str, index: int) -> str:
    """Generate readable method name from URL."""
    path = urlparse(url).path or "/"
    parts = [p for p in path.split('/') if p and not p.isdigit()][-2:]
    if parts:
        name = ''.join(word.capitalize() for word in parts)
        return f"{method.lower()}{name}"
    return f"{method.lower()}Request"


def _filter_headers(headers: dict) -> dict:
    """Remove sensitive and standard headers."""
    skip = {
        'authorization', 'cookie', 'x-api-key', 'x-auth-token', 'x-admin-key',
        'host', 'connection', 'accept-encoding', 'content-length', 'user-agent'
    }
    return {k: v for k, v in headers.items() if k.lower() not in skip}


def _empty_test_template(class_name: str, package_name: str) -> str:
    """Return template for empty session."""
    return f"""package {package_name};

import org.junit.jupiter.api.*;

/**
 * Auto-generated REST Assured tests from ErrorLens session.
 * No requests were recorded.
 */
public class {class_name} {{

    @Test
    @Disabled("No requests recorded")
    public void placeholder() {{
        // No requests to test
    }}
}}
"""


def generate_pom_xml(group_id: str = "com.errorlens", artifact_id: str = "session-tests") -> str:
    """Generate Maven pom.xml for running tests."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>{group_id}</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <rest-assured.version>5.4.0</rest-assured.version>
        <junit.version>5.10.0</junit.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>io.rest-assured</groupId>
            <artifactId>rest-assured</artifactId>
            <version>${{rest-assured.version}}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>${{junit.version}}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.hamcrest</groupId>
            <artifactId>hamcrest</artifactId>
            <version>2.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.2.2</version>
            </plugin>
        </plugins>
    </build>
</project>
"""
