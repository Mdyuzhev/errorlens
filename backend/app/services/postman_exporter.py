"""Export Pechkin collection to Postman Collection v2.1 JSON."""

from typing import Any


def export_to_postman(collection: dict) -> dict:
    """
    Convert Pechkin collection dict to Postman Collection v2.1 format.

    collection: результат collection_to_dict() из pechkin_schemas.py
    Структура: {id, name, folders: [{id, name, requests: [...], children: [...]}], requests: [...], variables: [...]}
    """
    postman = {
        "info": {
            "_postman_id": collection.get("id", ""),
            "name": collection.get("name", "Collection"),
            "description": collection.get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [],
        "variable": [],
    }

    # Convert variables to Postman environment format
    for var in (collection.get("variables") or []):
        postman["variable"].append({
            "key": var.get("name", ""),
            "value": var.get("value", ""),
            "type": "secret" if var.get("is_secret") else "string",
            "enabled": var.get("is_enabled", True),
        })

    # Process folders recursively
    for folder in (collection.get("folders") or []):
        postman["item"].append(_convert_folder(folder))

    # Root-level requests
    for req in (collection.get("requests") or []):
        postman["item"].append(_convert_request(req))

    return postman


def _convert_folder(folder: dict) -> dict:
    """Convert folder + its children to Postman folder item."""
    items = []

    # Sub-folders (children)
    for child in (folder.get("children") or folder.get("folders") or []):
        items.append(_convert_folder(child))

    # Requests in this folder
    for req in (folder.get("requests") or []):
        items.append(_convert_request(req))

    return {
        "name": folder.get("name", "Folder"),
        "item": items,
        "description": folder.get("description", ""),
    }


def _convert_request(req: dict) -> dict:
    """Convert Pechkin request to Postman request item."""
    request_obj = _build_request(req)
    events = _build_events(req)

    result = {
        "name": req.get("name", "Request"),
        "request": request_obj,
        "response": [],
    }
    if events:
        result["event"] = events

    return result


def _build_request(req: dict) -> dict:
    """Build Postman request object from Pechkin request."""
    method = req.get("method", "GET").upper()
    url_raw = req.get("url", "")

    # Parse URL for Postman format
    url_obj = _parse_url(url_raw)

    # Headers
    headers = []
    raw_headers = req.get("headers") or {}
    if isinstance(raw_headers, dict):
        for k, v in raw_headers.items():
            headers.append({"key": k, "value": str(v), "type": "text"})
    elif isinstance(raw_headers, list):
        for h in raw_headers:
            headers.append({"key": h.get("key", ""), "value": h.get("value", ""), "type": "text"})

    request_obj: dict[str, Any] = {
        "method": method,
        "header": headers,
        "url": url_obj,
        "description": "",
    }

    # Body
    body_type = req.get("body_type", "none")
    body_content = req.get("body")
    if body_type and body_type != "none" and body_content:
        request_obj["body"] = _build_body(body_type, body_content)

    # Auth
    auth = req.get("auth") or {}
    auth_type = auth.get("type", "none")
    if auth_type and auth_type != "none":
        request_obj["auth"] = _build_auth(auth)

    return request_obj


def _parse_url(url_raw: str) -> dict:
    """Convert URL string to Postman URL object."""
    if not url_raw:
        return {"raw": "", "protocol": "", "host": [], "path": []}

    from urllib.parse import urlparse, parse_qs
    try:
        parsed = urlparse(url_raw)
        host = parsed.hostname.split(".") if parsed.hostname else []
        path = [p for p in parsed.path.split("/") if p]

        url_obj: dict[str, Any] = {
            "raw": url_raw,
            "protocol": parsed.scheme or "https",
            "host": host,
            "path": path,
        }

        if parsed.port:
            url_obj["port"] = str(parsed.port)

        # Query params
        if parsed.query:
            qs = parse_qs(parsed.query, keep_blank_values=True)
            url_obj["query"] = [
                {"key": k, "value": v[0] if v else ""}
                for k, v in qs.items()
            ]

        return url_obj
    except Exception:
        return {"raw": url_raw, "host": [], "path": []}


def _build_body(body_type: str, content: str) -> dict:
    """Build Postman body object."""
    if body_type == "raw":
        # Detect language from content
        options = {"raw": {"language": "json"}} if content.strip().startswith(("{", "[")) else {}
        return {"mode": "raw", "raw": content, "options": options}
    elif body_type in ("x-www-form-urlencoded", "urlencoded"):
        pairs = []
        for pair in content.split("&"):
            if "=" in pair:
                k, _, v = pair.partition("=")
                pairs.append({"key": k, "value": v, "enabled": True})
        return {"mode": "urlencoded", "urlencoded": pairs}
    elif body_type == "form-data":
        return {"mode": "formdata", "formdata": []}
    elif body_type == "graphql":
        return {"mode": "graphql", "graphql": {"query": content}}
    else:
        return {"mode": "raw", "raw": content or ""}


def _build_auth(auth: dict) -> dict:
    """Convert Pechkin auth to Postman auth block."""
    auth_type = auth.get("type", "none")

    if auth_type == "bearer":
        return {
            "type": "bearer",
            "bearer": [{"key": "token", "value": auth.get("token", ""), "type": "string"}],
        }
    elif auth_type == "basic":
        return {
            "type": "basic",
            "basic": [
                {"key": "username", "value": auth.get("username", ""), "type": "string"},
                {"key": "password", "value": auth.get("password", ""), "type": "string"},
            ],
        }
    elif auth_type in ("api_key", "apikey"):
        return {
            "type": "apikey",
            "apikey": [
                {"key": "key", "value": auth.get("key", ""), "type": "string"},
                {"key": "value", "value": auth.get("value", ""), "type": "string"},
                {"key": "in", "value": auth.get("in", "header"), "type": "string"},
            ],
        }
    return {"type": "noauth"}


def _build_events(req: dict) -> list:
    """Build Postman event list from scripts."""
    events = []
    if req.get("pre_request_script"):
        events.append({
            "listen": "prerequest",
            "script": {
                "exec": req["pre_request_script"].split("\n"),
                "type": "text/javascript",
            },
        })
    if req.get("test_script"):
        events.append({
            "listen": "test",
            "script": {
                "exec": req["test_script"].split("\n"),
                "type": "text/javascript",
            },
        })
    return events
