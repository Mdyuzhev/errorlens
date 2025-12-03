"""Postman Collection generator from recorded HTTP exchanges."""

import json
import re
from urllib.parse import urlparse, parse_qs

from app.models import (
    ExportPostmanRequest,
    ExportPostmanResponse,
    PostmanBody,
    PostmanCollection,
    PostmanEvent,
    PostmanHeader,
    PostmanInfo,
    PostmanItem,
    PostmanRequest,
    PostmanUrl,
    PostmanVariable,
    RecordedHttpExchange,
)
from app.session_analyzer import detect_variables


# Headers to exclude from Postman export (browser-specific)
EXCLUDED_HEADERS = {
    "accept-encoding",
    "accept-language",
    "cache-control",
    "connection",
    "host",
    "origin",
    "referer",
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "sec-fetch-dest",
    "sec-fetch-mode",
    "sec-fetch-site",
    "upgrade-insecure-requests",
    "user-agent",
    "cookie",  # Exclude cookies for security
}

# URL patterns to filter out (analytics, ads, static assets)
JUNK_URL_PATTERNS = [
    r"google-analytics\.com",
    r"googletagmanager\.com",
    r"facebook\.com/tr",
    r"doubleclick\.net",
    r"hotjar\.com",
    r"segment\.io",
    r"mixpanel\.com",
    r"amplitude\.com",
    r"sentry\.io",
    r"newrelic\.com",
    r"\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|css)(\?|$)",
    r"/_next/static/",
    r"/static/js/",
    r"/static/css/",
    r"/favicon",
]


def is_junk_request(url: str) -> bool:
    """Check if URL matches junk patterns (analytics, static assets)."""
    for pattern in JUNK_URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def filter_headers(headers: dict[str, str]) -> list[PostmanHeader]:
    """Filter out browser-specific headers, keep API-relevant ones."""
    result = []
    for key, value in headers.items():
        if key.lower() not in EXCLUDED_HEADERS:
            result.append(PostmanHeader(key=key, value=value))
    return result


def extract_base_url(urls: list[str]) -> str | None:
    """Extract common base URL from list of request URLs."""
    if not urls:
        return None

    # Parse all URLs and find common origin
    origins = set()
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            origins.add(f"{parsed.scheme}://{parsed.netloc}")

    # If all requests share same origin, use it
    if len(origins) == 1:
        return origins.pop()

    # Multiple origins - return the most common one
    origin_counts = {}
    for url in urls:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        origin_counts[origin] = origin_counts.get(origin, 0) + 1

    return max(origin_counts, key=origin_counts.get)


def parse_url_for_postman(url: str, base_url: str | None) -> PostmanUrl:
    """Parse URL into Postman URL structure."""
    parsed = urlparse(url)

    # Build raw URL (with variable substitution if base_url provided)
    raw = url
    if base_url and url.startswith(base_url):
        raw = "{{baseUrl}}" + url[len(base_url):]

    # Parse query parameters
    query_params = []
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=True)
        for key, values in qs.items():
            for value in values:
                query_params.append({"key": key, "value": value})

    # Parse path segments
    path_segments = [seg for seg in parsed.path.split("/") if seg]

    return PostmanUrl(
        raw=raw,
        protocol=parsed.scheme or None,
        host=parsed.netloc.split(".") if parsed.netloc else None,
        path=path_segments or None,
        query=query_params or None,
    )


def generate_test_script(exchange: RecordedHttpExchange) -> PostmanEvent:
    """Generate pm.test() assertions for a request."""
    tests = []

    # Test 1: Status code check
    status = exchange.response.status
    if 200 <= status < 300:
        tests.append(
            f'pm.test("Status code is {status}", function () {{\n'
            f"    pm.response.to.have.status({status});\n"
            f"}});"
        )
    elif status < 400:
        tests.append(
            f'pm.test("Status code is 2xx or 3xx", function () {{\n'
            f"    pm.expect(pm.response.code).to.be.oneOf([{status}, 200, 201, 204, 301, 302]);\n"
            f"}});"
        )
    else:
        # Error status - test that we get the expected error
        tests.append(
            f'pm.test("Status code is {status}", function () {{\n'
            f"    pm.response.to.have.status({status});\n"
            f"}});"
        )

    # Test 2: Response time check
    if exchange.response.duration_ms > 0:
        # Set threshold at 2x recorded time or 2000ms, whichever is higher
        threshold = max(exchange.response.duration_ms * 2, 2000)
        tests.append(
            f'pm.test("Response time is acceptable", function () {{\n'
            f"    pm.expect(pm.response.responseTime).to.be.below({threshold});\n"
            f"}});"
        )

    # Test 3: JSON response validation (if applicable)
    content_type = exchange.response.headers.get("content-type", "")
    if "application/json" in content_type.lower() and exchange.response.body:
        try:
            response_json = json.loads(exchange.response.body)
            if isinstance(response_json, dict):
                # Check for common fields
                if "id" in response_json:
                    tests.append(
                        'pm.test("Response has id field", function () {\n'
                        "    var jsonData = pm.response.json();\n"
                        '    pm.expect(jsonData).to.have.property("id");\n'
                        "});"
                    )
                if "data" in response_json:
                    tests.append(
                        'pm.test("Response has data field", function () {\n'
                        "    var jsonData = pm.response.json();\n"
                        '    pm.expect(jsonData).to.have.property("data");\n'
                        "});"
                    )
                if "error" in response_json or "errors" in response_json:
                    tests.append(
                        'pm.test("Response contains error info", function () {\n'
                        "    var jsonData = pm.response.json();\n"
                        '    pm.expect(jsonData).to.have.any.keys("error", "errors", "message");\n'
                        "});"
                    )
        except (json.JSONDecodeError, TypeError):
            pass

    script_body = "\n\n".join(tests)

    return PostmanEvent(
        listen="test",
        script={
            "type": "text/javascript",
            "exec": script_body.split("\n"),
        },
    )


def exchange_to_postman_item(
    exchange: RecordedHttpExchange,
    base_url: str | None,
    generate_tests: bool,
) -> PostmanItem:
    """Convert a recorded HTTP exchange to Postman item."""
    # Generate request name from method and path
    parsed = urlparse(exchange.request.url)
    path = parsed.path or "/"
    name = f"{exchange.request.method} {path}"

    # Filter and convert headers
    headers = filter_headers(exchange.request.headers)

    # Handle request body
    body = None
    if exchange.request.body:
        content_type = exchange.request.content_type or ""
        if "application/json" in content_type.lower():
            body = PostmanBody(
                mode="raw",
                raw=exchange.request.body,
                options={"raw": {"language": "json"}},
            )
        elif "application/x-www-form-urlencoded" in content_type.lower():
            body = PostmanBody(mode="urlencoded", raw=exchange.request.body)
        else:
            body = PostmanBody(mode="raw", raw=exchange.request.body)

    # Parse URL
    url = parse_url_for_postman(exchange.request.url, base_url)

    # Build request
    request = PostmanRequest(
        method=exchange.request.method,
        header=headers,
        body=body,
        url=url,
    )

    # Generate tests if requested
    events = []
    if generate_tests:
        events.append(generate_test_script(exchange))

    return PostmanItem(
        name=name,
        event=events,
        request=request,
        response=[],
    )


def generate_postman_collection(request: ExportPostmanRequest) -> ExportPostmanResponse:
    """Generate Postman Collection from recorded HTTP exchanges."""
    # Filter out junk requests
    filtered_exchanges = [
        ex for ex in request.recorded_requests
        if not is_junk_request(ex.request.url)
    ]

    if not filtered_exchanges:
        # If all filtered out, use original list
        filtered_exchanges = request.recorded_requests

    # Detect variables (tokens, IDs)
    detected_vars = detect_variables(filtered_exchanges)

    # Extract base URL if requested
    base_url = None
    variables = []
    if request.base_url_variable:
        urls = [ex.request.url for ex in filtered_exchanges]
        base_url = extract_base_url(urls)
        if base_url:
            variables.append(PostmanVariable(key="baseUrl", value=base_url))

    # Add detected variables
    for var_name, var_data in detected_vars.items():
        variables.append(PostmanVariable(
            key=var_name,
            value=var_data["value"]
        ))

    # Convert exchanges to Postman items
    items = [
        exchange_to_postman_item(ex, base_url, request.generate_tests)
        for ex in filtered_exchanges
    ]

    # Add pre-request scripts to extract variables from responses
    items = add_variable_extraction_scripts(items, filtered_exchanges, detected_vars)

    # Build collection
    collection = PostmanCollection(
        info=PostmanInfo(
            name=request.collection_name,
            description=f"Generated by ErrorLens from {len(items)} recorded requests. "
                        f"Detected {len(detected_vars)} variables.",
        ),
        item=items,
        variable=variables,
    )

    return ExportPostmanResponse(
        collection=collection,
        requests_count=len(items),
        variables_count=len(variables),
    )


def add_variable_extraction_scripts(
    items: list[PostmanItem],
    exchanges: list[RecordedHttpExchange],
    detected_vars: dict,
) -> list[PostmanItem]:
    """Add scripts to extract variables from responses."""
    # Map request ID to item index
    id_to_index = {ex.id: i for i, ex in enumerate(exchanges)}

    for var_name, var_data in detected_vars.items():
        source_id = var_data["source_request_id"]
        if source_id not in id_to_index:
            continue

        idx = id_to_index[source_id]
        source_path = var_data["source_path"]

        # Generate extraction script
        if "response.body." in source_path:
            json_path = source_path.replace("response.body.", "")
            script_lines = [
                "// Extract variable from response",
                "var jsonData = pm.response.json();",
                f'var value = jsonData.{json_path};',
                "if (value) {",
                f'    pm.collectionVariables.set("{var_name}", value);',
                f'    console.log("Extracted {var_name}:", value);',
                "}",
            ]
        elif "response.headers." in source_path:
            header_name = source_path.replace("response.headers.", "")
            script_lines = [
                "// Extract variable from response header",
                f'var value = pm.response.headers.get("{header_name}");',
                "if (value) {",
                f'    pm.collectionVariables.set("{var_name}", value);',
                f'    console.log("Extracted {var_name}:", value);',
                "}",
            ]
        else:
            continue

        # Add to existing test script or create new one
        existing_events = items[idx].event
        test_event = next((e for e in existing_events if e.listen == "test"), None)

        if test_event:
            # Prepend to existing script
            existing_exec = test_event.script.get("exec", [])
            test_event.script["exec"] = script_lines + [""] + existing_exec
        else:
            # Create new test event
            items[idx].event.append(PostmanEvent(
                listen="test",
                script={
                    "type": "text/javascript",
                    "exec": script_lines,
                }
            ))

    return items
