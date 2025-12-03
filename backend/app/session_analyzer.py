"""Session analysis for test generation - variable detection, grouping, assertions."""

import json
import re
from collections import defaultdict
from urllib.parse import urlparse

from app.models import RecordedHttpExchange


# Common token/ID field names
TOKEN_FIELDS = {
    "token", "access_token", "accessToken", "auth_token", "authToken",
    "refresh_token", "refreshToken", "jwt", "bearer", "session_id",
    "sessionId", "csrf", "csrfToken", "csrf_token", "api_key", "apiKey",
}

ID_FIELDS = {
    "id", "_id", "userId", "user_id", "orderId", "order_id",
    "productId", "product_id", "itemId", "item_id",
}


def extract_json_values(body: str | None) -> dict[str, str]:
    """Extract key-value pairs from JSON body."""
    if not body:
        return {}

    try:
        data = json.loads(body)
        if isinstance(data, dict):
            result = {}
            _flatten_dict(data, "", result)
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    return {}


def _flatten_dict(d: dict, prefix: str, result: dict):
    """Flatten nested dict into dot-notation keys."""
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _flatten_dict(value, full_key, result)
        elif isinstance(value, (str, int, float, bool)) and value:
            result[full_key] = str(value)


def detect_variables(exchanges: list[RecordedHttpExchange]) -> dict[str, dict]:
    """
    Detect variables: values from responses that appear in subsequent requests.

    Returns dict of variable_name -> {
        "source_request_id": int,
        "source_path": str (e.g., "response.body.token"),
        "value": str,
        "used_in": list[int] (request IDs where this value is used)
    }
    """
    variables = {}

    # Collect all response values
    response_values = {}  # value -> (request_id, path)
    for ex in exchanges:
        # From response body
        body_values = extract_json_values(ex.response.body)
        for path, value in body_values.items():
            if len(value) >= 8:  # Skip short values
                key = f"response.body.{path}"
                response_values[value] = (ex.id, key)

        # From response headers
        for header, value in ex.response.headers.items():
            if len(value) >= 8:
                key = f"response.headers.{header}"
                response_values[value] = (ex.id, key)

    # Check if response values appear in subsequent requests
    for ex in exchanges:
        # Check request headers
        for header, value in ex.request.headers.items():
            # Direct match
            if value in response_values:
                source_id, source_path = response_values[value]
                if source_id < ex.id:  # Only if from earlier request
                    var_name = _generate_var_name(source_path)
                    if var_name not in variables:
                        variables[var_name] = {
                            "source_request_id": source_id,
                            "source_path": source_path,
                            "value": value,
                            "used_in": []
                        }
                    if ex.id not in variables[var_name]["used_in"]:
                        variables[var_name]["used_in"].append(ex.id)
            else:
                # Check if any response value is contained in this header value
                # (handles "Bearer <token>" pattern)
                for resp_value, (source_id, source_path) in response_values.items():
                    if source_id < ex.id and resp_value in value:
                        var_name = _generate_var_name(source_path)
                        if var_name not in variables:
                            variables[var_name] = {
                                "source_request_id": source_id,
                                "source_path": source_path,
                                "value": resp_value,
                                "used_in": []
                            }
                        if ex.id not in variables[var_name]["used_in"]:
                            variables[var_name]["used_in"].append(ex.id)
                        break

        # Check request body
        body_values = extract_json_values(ex.request.body)
        for path, value in body_values.items():
            if value in response_values:
                source_id, source_path = response_values[value]
                if source_id < ex.id:
                    var_name = _generate_var_name(source_path)
                    if var_name not in variables:
                        variables[var_name] = {
                            "source_request_id": source_id,
                            "source_path": source_path,
                            "value": value,
                            "used_in": []
                        }
                    if ex.id not in variables[var_name]["used_in"]:
                        variables[var_name]["used_in"].append(ex.id)

        # Check URL for IDs
        for value, (source_id, source_path) in response_values.items():
            if source_id < ex.id and value in ex.request.url:
                var_name = _generate_var_name(source_path)
                if var_name not in variables:
                    variables[var_name] = {
                        "source_request_id": source_id,
                        "source_path": source_path,
                        "value": value,
                        "used_in": []
                    }
                if ex.id not in variables[var_name]["used_in"]:
                    variables[var_name]["used_in"].append(ex.id)

    return variables


def _generate_var_name(source_path: str) -> str:
    """Generate variable name from source path."""
    # Extract last part of path
    parts = source_path.split(".")
    last_part = parts[-1] if parts else "value"

    # Check for known field types
    lower = last_part.lower()
    if any(t in lower for t in ["token", "jwt", "bearer", "auth"]):
        return "authToken"
    if any(t in lower for t in ["csrf"]):
        return "csrfToken"
    if any(t in lower for t in ["session"]):
        return "sessionId"
    if lower in ("id", "_id"):
        # Try to get context from parent
        if len(parts) >= 2:
            parent = parts[-2]
            return f"{parent}Id"
        return "resourceId"

    return last_part


def group_requests_by_scenario(exchanges: list[RecordedHttpExchange]) -> dict[str, list[int]]:
    """
    Group requests into logical scenarios based on URL patterns and methods.

    Returns dict of scenario_name -> list of request IDs
    """
    groups = defaultdict(list)

    for ex in exchanges:
        parsed = urlparse(ex.request.url)
        path = parsed.path.lower()
        method = ex.request.method.upper()

        # Authentication
        if any(p in path for p in ["/auth", "/login", "/logout", "/register", "/signup", "/token", "/oauth"]):
            groups["auth"].append(ex.id)
            continue

        # User operations
        if any(p in path for p in ["/user", "/profile", "/account", "/me"]):
            groups["user"].append(ex.id)
            continue

        # CRUD operations - detect by method + path pattern
        if method == "GET" and re.search(r"/\d+$", path):
            groups["read"].append(ex.id)
        elif method == "GET":
            groups["list"].append(ex.id)
        elif method == "POST":
            groups["create"].append(ex.id)
        elif method in ("PUT", "PATCH"):
            groups["update"].append(ex.id)
        elif method == "DELETE":
            groups["delete"].append(ex.id)
        else:
            groups["other"].append(ex.id)

    # Remove empty groups
    return {k: v for k, v in groups.items() if v}


def extract_assertions(exchange: RecordedHttpExchange) -> list[dict]:
    """
    Extract meaningful assertions from a response.

    Returns list of assertion dicts with:
    - type: "status" | "header" | "json_field" | "json_type" | "response_time"
    - path: field path for JSON assertions
    - expected: expected value
    - description: human-readable description
    """
    assertions = []

    # Status code assertion
    assertions.append({
        "type": "status",
        "expected": exchange.response.status,
        "description": f"Status code is {exchange.response.status}"
    })

    # Response time assertion
    if exchange.response.duration_ms > 0:
        threshold = max(exchange.response.duration_ms * 2, 1000)
        assertions.append({
            "type": "response_time",
            "expected": threshold,
            "description": f"Response time under {threshold}ms"
        })

    # Content-Type header
    content_type = exchange.response.headers.get("content-type", "")
    if content_type:
        assertions.append({
            "type": "header",
            "path": "content-type",
            "expected": content_type.split(";")[0].strip(),
            "description": f"Content-Type is {content_type.split(';')[0].strip()}"
        })

    # JSON body assertions
    if "application/json" in content_type.lower() and exchange.response.body:
        try:
            data = json.loads(exchange.response.body)
            if isinstance(data, dict):
                # Check for important fields
                for field in ["id", "_id", "data", "results", "items", "error", "message", "success", "status"]:
                    if field in data:
                        value = data[field]
                        assertions.append({
                            "type": "json_field",
                            "path": field,
                            "expected": type(value).__name__,
                            "description": f"Response has '{field}' field"
                        })

                # For arrays, check length
                for field, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        assertions.append({
                            "type": "json_array",
                            "path": field,
                            "expected": "non-empty",
                            "description": f"'{field}' array is not empty"
                        })
                        break  # Only one array assertion

            elif isinstance(data, list):
                assertions.append({
                    "type": "json_type",
                    "expected": "array",
                    "description": "Response is an array"
                })
                if len(data) > 0:
                    assertions.append({
                        "type": "json_array",
                        "path": "$",
                        "expected": "non-empty",
                        "description": "Response array is not empty"
                    })
        except (json.JSONDecodeError, TypeError):
            pass

    return assertions


def analyze_session(exchanges: list[RecordedHttpExchange]) -> dict:
    """
    Full session analysis for test generation.

    Returns:
    - variables: detected variables (tokens, IDs)
    - groups: requests grouped by scenario
    - assertions: extracted assertions per request
    - summary: analysis summary
    """
    variables = detect_variables(exchanges)
    groups = group_requests_by_scenario(exchanges)

    assertions_by_request = {}
    for ex in exchanges:
        assertions_by_request[ex.id] = extract_assertions(ex)

    # Build summary
    summary = {
        "total_requests": len(exchanges),
        "variables_found": len(variables),
        "scenarios_detected": list(groups.keys()),
        "methods": list(set(ex.request.method for ex in exchanges)),
    }

    return {
        "variables": variables,
        "groups": groups,
        "assertions": assertions_by_request,
        "summary": summary,
    }
