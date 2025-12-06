"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field


class ConsoleLogEntry(BaseModel):
    """Single console log entry captured by bookmarklet."""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    level: str = Field(..., description="Log level: log, warn, error, info, debug")
    message: str = Field(..., description="Log message content")
    stack: str | None = Field(None, description="Stack trace if available")


class NetworkError(BaseModel):
    """Network request failure captured by bookmarklet."""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    method: str = Field(..., description="HTTP method: GET, POST, etc.")
    url: str = Field(..., description="Request URL")
    status: int | None = Field(None, description="HTTP status code")
    status_text: str | None = Field(None, description="HTTP status text")


class JSException(BaseModel):
    """JavaScript exception captured by window.onerror."""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    message: str = Field(..., description="Error message")
    source: str | None = Field(None, description="Script URL where error occurred")
    lineno: int | None = Field(None, description="Line number")
    colno: int | None = Field(None, description="Column number")
    stack: str | None = Field(None, description="Stack trace")


# Story 7.1: Extended request recording models
class RecordedRequest(BaseModel):
    """Full HTTP request captured for test generation."""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    method: str = Field(..., description="HTTP method: GET, POST, PUT, DELETE, etc.")
    url: str = Field(..., description="Full request URL")
    headers: dict[str, str] = Field(default_factory=dict, description="Request headers")
    body: str | None = Field(None, description="Request body (JSON string or form data)")
    content_type: str | None = Field(None, description="Content-Type header value")


class RecordedResponse(BaseModel):
    """Full HTTP response captured for test generation."""

    status: int = Field(..., description="HTTP status code")
    status_text: str | None = Field(None, description="HTTP status text")
    headers: dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: str | None = Field(None, description="Response body (truncated if large)")
    duration_ms: int = Field(..., description="Response time in milliseconds")


class RecordedHttpExchange(BaseModel):
    """Complete HTTP request/response pair for test generation."""

    id: int = Field(..., description="Sequential ID within session")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    request: RecordedRequest = Field(..., description="Request details")
    response: RecordedResponse = Field(..., description="Response details")


class AnalyzeRequest(BaseModel):
    """Request body for /analyze endpoint."""

    url: str = Field(..., description="Page URL where errors were captured")
    user_agent: str = Field(..., description="Browser user agent string")
    console_logs: list[ConsoleLogEntry] = Field(
        default_factory=list, description="Captured console logs"
    )
    network_errors: list[NetworkError] = Field(
        default_factory=list, description="Failed network requests"
    )
    js_exceptions: list[JSException] = Field(
        default_factory=list, description="Uncaught JavaScript exceptions"
    )
    screenshot: str | None = Field(None, description="Base64-encoded screenshot")
    recording_duration_ms: int = Field(..., description="Recording duration in ms")
    # Story 7.1: Extended recording data
    recorded_requests: list[RecordedHttpExchange] = Field(
        default_factory=list, description="All recorded HTTP exchanges for test generation"
    )
    record_mode: str = Field(default="errors", description="Recording mode: 'errors' or 'all'")


class AnalyzeResponse(BaseModel):
    """Response body from /analyze endpoint."""

    summary: str = Field(..., description="Brief summary of detected issues")
    probable_cause: str = Field(..., description="Most likely root cause")
    suggested_fix: str = Field(..., description="Recommended fix")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    raw_events_count: int = Field(..., description="Total events analyzed")
    details: str = Field(..., description="Detailed analysis")


# Story 7.3: Postman Collection models (v2.1 schema)
class PostmanHeader(BaseModel):
    """Postman request header."""

    key: str
    value: str
    type: str = "text"


class PostmanBody(BaseModel):
    """Postman request body."""

    mode: str = "raw"
    raw: str | None = None
    options: dict | None = None


class PostmanUrl(BaseModel):
    """Postman URL object."""

    raw: str
    protocol: str | None = None
    host: list[str] | None = None
    path: list[str] | None = None
    query: list[dict] | None = None


class PostmanRequest(BaseModel):
    """Postman request object."""

    method: str
    header: list[PostmanHeader] = Field(default_factory=list)
    body: PostmanBody | None = None
    url: PostmanUrl


class PostmanEvent(BaseModel):
    """Postman test script event."""

    listen: str = "test"
    script: dict


class PostmanItem(BaseModel):
    """Single request item in Postman collection."""

    name: str
    event: list[PostmanEvent] = Field(default_factory=list)
    request: PostmanRequest
    response: list = Field(default_factory=list)


class PostmanVariable(BaseModel):
    """Postman collection variable."""

    key: str
    value: str
    type: str = "string"


class PostmanInfo(BaseModel):
    """Postman collection info."""

    name: str
    description: str = ""
    schema_url: str = Field(
        default="https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        alias="schema",
    )

    class Config:
        populate_by_name = True


class PostmanCollection(BaseModel):
    """Postman Collection v2.1 format."""

    info: PostmanInfo
    item: list[PostmanItem] = Field(default_factory=list)
    variable: list[PostmanVariable] = Field(default_factory=list)


class ExportPostmanRequest(BaseModel):
    """Request body for Postman export endpoint."""

    recorded_requests: list[RecordedHttpExchange] = Field(
        ..., description="Recorded HTTP exchanges to convert"
    )
    collection_name: str = Field(
        default="ErrorLens Session", description="Name for the Postman collection"
    )
    base_url_variable: bool = Field(
        default=True, description="Extract base URL as {{baseUrl}} variable"
    )
    generate_tests: bool = Field(default=True, description="Generate pm.test() assertions")


class ExportPostmanResponse(BaseModel):
    """Response from Postman export endpoint."""

    collection: PostmanCollection
    requests_count: int
    variables_count: int


class ExportPytestRequest(BaseModel):
    """Request body for pytest export endpoint."""

    recorded_requests: list[RecordedHttpExchange] = Field(
        ..., description="Recorded HTTP exchanges to convert"
    )
    test_name: str = Field(default="test_session", description="Name for the test file/class")
    base_url_variable: bool = Field(default=True, description="Extract base URL as variable")
    use_llm: bool = Field(default=True, description="Use LLM to generate intelligent comments")


# Story 8.6.1: Ticket generator models
class GenerateTicketRequest(BaseModel):
    """Request body for ticket generation endpoint."""

    session_id: str = Field(..., description="Session ID to generate ticket from")
    format: str = Field(default="jira", description="Ticket format: jira, github, markdown")
    additional_info: str = Field(default="", description="Additional info to include in ticket")


class GenerateTicketResponse(BaseModel):
    """Response from ticket generation endpoint."""

    title: str
    description: str | None = None
    body: str | None = None
    content: str | None = None
    priority: str | None = None
    labels: list[str] | None = None
    format: str


# Story 8.6.2: Test runner models
class RunTestRequest(BaseModel):
    """Request body for test runner endpoint."""

    session_id: str | None = Field(default=None, description="Session ID to run tests for")
    test_code: str | None = Field(default=None, description="Raw test code to execute")


class TestRunSummary(BaseModel):
    """Summary of test run results."""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    total: int = 0


class TestRunStatus(BaseModel):
    """Status of a test run."""

    status: str  # pending, running, passed, failed, error
    started_at: str | None = None
    finished_at: str | None = None
    output: str = ""
    returncode: int | None = None
    summary: TestRunSummary | None = None


# Story 7.2: Session analysis models
class DetectedVariable(BaseModel):
    """Variable detected in session (token, ID, etc.)."""

    name: str = Field(..., description="Variable name")
    source_request_id: int = Field(..., description="Request ID where value originated")
    source_path: str = Field(..., description="Path to value (e.g., response.body.token)")
    value: str = Field(..., description="Actual value (may be truncated for security)")
    used_in: list[int] = Field(
        default_factory=list, description="Request IDs where this value is used"
    )


class RequestAssertion(BaseModel):
    """Assertion extracted from response."""

    type: str = Field(..., description="Assertion type: status, header, json_field, etc.")
    path: str | None = Field(None, description="Field path for JSON/header assertions")
    expected: str = Field(..., description="Expected value or type")
    description: str = Field(..., description="Human-readable description")


class SessionAnalysisRequest(BaseModel):
    """Request body for session analysis endpoint."""

    recorded_requests: list[RecordedHttpExchange] = Field(
        ..., description="Recorded HTTP exchanges to analyze"
    )


class SessionAnalysisResponse(BaseModel):
    """Response from session analysis endpoint."""

    variables: dict[str, DetectedVariable] = Field(
        default_factory=dict, description="Detected variables (tokens, IDs)"
    )
    groups: dict[str, list[int]] = Field(
        default_factory=dict, description="Requests grouped by scenario"
    )
    assertions: dict[int, list[RequestAssertion]] = Field(
        default_factory=dict, description="Assertions per request ID"
    )
    summary: dict = Field(default_factory=dict, description="Analysis summary")


# Story 7.5.2: REST Assured export models
class ExportRestAssuredRequest(BaseModel):
    """Request body for REST Assured export endpoint."""

    recorded_requests: list[RecordedHttpExchange] = Field(
        ..., description="Recorded HTTP exchanges to convert"
    )
    class_name: str = Field(default="SessionTest", description="Java class name for the test file")
    package_name: str = Field(default="com.errorlens.tests", description="Java package name")
    include_pom: bool = Field(default=True, description="Include pom.xml in the ZIP output")


# Story 7.5.3: k6 load test export models
class ExportK6Request(BaseModel):
    """Request body for k6 load test export endpoint."""

    recorded_requests: list[RecordedHttpExchange] = Field(
        ..., description="Recorded HTTP exchanges to convert"
    )
    vus: int = Field(default=10, ge=1, le=1000, description="Number of virtual users")
    duration: str = Field(default="30s", description="Test duration (e.g., '30s', '1m', '5m')")


# Story 13: TestIt test case export models
class ExportTestItRequest(BaseModel):
    """Request body for TestIt test case export endpoint."""

    recorded_requests: list[RecordedHttpExchange] = Field(
        ..., description="Recorded HTTP exchanges to convert to test case"
    )
    analysis: AnalyzeResponse | None = Field(
        default=None, description="Optional AI analysis for priority/description"
    )
