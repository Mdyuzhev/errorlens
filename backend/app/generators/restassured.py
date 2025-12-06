"""Generate REST Assured (Java) test files from recorded HTTP sessions."""

import json

from app.models_pydantic import RecordedHttpExchange

from .base import (
    BaseGenerator,
    escape_string,
    extract_path,
    filter_headers,
    generate_method_name,
    has_auth_header_in_request,
    is_auth_endpoint,
    parse_json_body,
)


class RestAssuredGenerator(BaseGenerator):
    """Generate REST Assured (Java) test files from recorded HTTP sessions."""

    def __init__(
        self,
        recorded_requests: list[RecordedHttpExchange],
        class_name: str = "SessionTest",
        package_name: str = "com.errorlens.tests",
    ):
        super().__init__(recorded_requests)
        self.class_name = class_name
        self.package_name = package_name

    def get_file_extension(self) -> str:
        return ".java"

    def get_language(self) -> str:
        return "java"

    def generate(self) -> str:
        """Generate REST Assured Java test file."""
        if not self.requests:
            return self._empty_template()

        lines = self._generate_header()
        lines.extend(self._generate_class_body())

        return "\n".join(lines)

    def _generate_header(self) -> list[str]:
        """Generate Java file header with imports."""
        return [
            f"package {self.package_name};",
            "",
            "import io.restassured.RestAssured;",
            "import io.restassured.http.ContentType;",
            "import io.restassured.response.Response;",
            "import org.junit.jupiter.api.*;",
            "import static io.restassured.RestAssured.*;",
            "import static org.hamcrest.Matchers.*;",
            "import static org.junit.jupiter.api.Assertions.*;",
            "",
            "/**",
            " * Auto-generated REST Assured tests from ErrorLens session.",
            f" * Base URL: {self.base_url}",
            " *",
            " * Tests run in order using @TestMethodOrder annotation.",
            " * Authentication token is shared between tests.",
            " */",
            "@TestMethodOrder(MethodOrderer.OrderAnnotation.class)",
            f"public class {self.class_name} {{",
            "",
        ]

    def _generate_class_body(self) -> list[str]:
        """Generate class body with setup and test methods."""
        lines = []

        # Add shared token field if auth flow detected
        if self.has_auth_flow:
            lines.extend(
                [
                    "    // Shared auth token extracted from login response",
                    "    private static String authToken;",
                    "",
                ]
            )

        # Setup method
        lines.extend(
            [
                "    @BeforeAll",
                "    public static void setup() {",
                f'        RestAssured.baseURI = "{self.base_url}";',
                "    }",
                "",
            ]
        )

        # Generate test methods
        for i, exchange in enumerate(self.requests):
            lines.extend(self._generate_test_method(i, exchange))

        lines.append("}")
        lines.append("")

        return lines

    def _generate_test_method(self, index: int, exchange: RecordedHttpExchange) -> list[str]:
        """Generate a single test method."""
        req = exchange.request
        resp = exchange.response
        path = extract_path(req.url)
        is_auth = is_auth_endpoint(req.url)
        needs_auth = self.has_auth_flow and not is_auth and has_auth_header_in_request(req.headers)

        method_name = generate_method_name(req.method, req.url, index)
        # Convert to camelCase for Java
        method_name = method_name[0].lower() + method_name[1:] if method_name else "request"

        lines = [
            f"    @Order({index + 1})",
            "    @Test",
            f'    @DisplayName("{req.method} {path}")',
            f"    public void test{index + 1:02d}_{method_name}() {{",
        ]

        # For auth endpoints, capture response to extract token
        if is_auth and self.has_auth_flow:
            lines.append("        Response response = given()")
        else:
            lines.append("        given()")

        # Add auth token header if needed
        if needs_auth:
            lines.append('            .header("Authorization", "Bearer " + authToken)')

        # Headers (excluding auth-related ones that we handle separately)
        safe_headers = filter_headers(req.headers, exclude_auth=needs_auth)
        for key, value in safe_headers.items():
            escaped_value = escape_string(value)
            lines.append(f'            .header("{key}", "{escaped_value}")')

        # Content type
        if req.content_type:
            lines.append(f'            .contentType("{req.content_type}")')

        # Body
        if req.body:
            body_dict = parse_json_body(req.body)
            if body_dict:
                body_json = json.dumps(body_dict, ensure_ascii=False)
                escaped_body = escape_string(body_json)
                lines.append(f'            .body("{escaped_body}")')
            else:
                escaped_body = escape_string(req.body)
                lines.append(f'            .body("{escaped_body}")')

        # Method and path
        lines.append("        .when()")

        # For auth endpoint, use extract() to get response
        if is_auth and self.has_auth_flow:
            lines.extend(
                [
                    f'            .{req.method.lower()}("{path}")',
                    "        .then()",
                    f"            .statusCode({resp.status})",
                    "            .extract().response();",
                    "",
                    "        // Extract auth token from response",
                    '        authToken = response.jsonPath().getString("token");',
                    "        if (authToken == null) {",
                    '            authToken = response.jsonPath().getString("access_token");',
                    "        }",
                    '        assertNotNull(authToken, "Auth token not found in login response");',
                ]
            )
        else:
            lines.extend(
                [
                    f'            .{req.method.lower()}("{path}")',
                    "        .then()",
                    f"            .statusCode({resp.status})",
                ]
            )

            # Response body assertions
            resp_body = parse_json_body(resp.body)
            if resp_body and isinstance(resp_body, dict):
                for key in list(resp_body.keys())[:3]:
                    lines.append(f'            .body("{key}", notNullValue())')

            lines.append("            .log().ifError();")

        lines.extend(["    }", ""])
        return lines

    def _empty_template(self) -> str:
        """Return template for empty session."""
        return f"""package {self.package_name};

import org.junit.jupiter.api.*;

/**
 * Auto-generated REST Assured tests from ErrorLens session.
 * No requests were recorded.
 */
public class {self.class_name} {{

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


# =============================================================================
# Public API (backward compatible)
# =============================================================================


def generate_restassured_file(
    recorded_requests: list[RecordedHttpExchange],
    class_name: str = "SessionTest",
    package_name: str = "com.errorlens.tests",
) -> str:
    """Generate a REST Assured Java test file from recorded requests."""
    generator = RestAssuredGenerator(
        recorded_requests=recorded_requests,
        class_name=class_name,
        package_name=package_name,
    )
    return generator.generate()
