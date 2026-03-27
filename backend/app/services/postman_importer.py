"""Parse Postman Collection v2.1 JSON into Pechkin models."""

from dataclasses import dataclass, field

from app.models.base import generate_uuid


@dataclass
class ImportedFolder:
    id: str
    name: str
    parent_id: str | None = None


@dataclass
class ImportedRequest:
    id: str
    name: str
    method: str
    url: str
    folder_id: str | None = None
    headers: dict = field(default_factory=dict)
    body: str | None = None
    body_type: str = "none"
    auth: dict = field(default_factory=dict)
    pre_request_script: str | None = None
    test_script: str | None = None


@dataclass
class ImportResult:
    collection_name: str
    folders: list[ImportedFolder] = field(default_factory=list)
    requests: list[ImportedRequest] = field(default_factory=list)


def import_postman_collection(json_data: dict) -> ImportResult:
    """Parse Postman v2.1 JSON and return folders + requests."""
    info = json_data.get("info", {})
    collection_name = info.get("name", "Imported Collection")
    items = json_data.get("item", [])

    folders: list[ImportedFolder] = []
    requests: list[ImportedRequest] = []

    def process_items(items_list: list, parent_folder_id: str | None = None):
        for item in items_list:
            if "item" in item:
                folder_id = generate_uuid()
                folders.append(ImportedFolder(
                    id=folder_id,
                    name=item.get("name", "Folder"),
                    parent_id=parent_folder_id,
                ))
                process_items(item["item"], folder_id)
            elif "request" in item:
                requests.append(_convert_request(item, parent_folder_id))

    process_items(items)
    return ImportResult(
        collection_name=collection_name,
        folders=folders,
        requests=requests,
    )


def _convert_request(item: dict, folder_id: str | None) -> ImportedRequest:
    """Convert a single Postman request item."""
    r = item["request"]

    # URL
    url_obj = r.get("url", {})
    url = url_obj if isinstance(url_obj, str) else url_obj.get("raw", "")

    # Headers
    headers = {}
    for h in r.get("header", []):
        if not h.get("disabled"):
            headers[h.get("key", "")] = h.get("value", "")

    # Body
    body = None
    body_type = "none"
    body_obj = r.get("body")
    if body_obj:
        mode = body_obj.get("mode", "raw")
        if mode == "raw":
            body = body_obj.get("raw", "")
            body_type = "raw"
        elif mode == "urlencoded":
            params = body_obj.get("urlencoded", [])
            body = "&".join(
                f"{p['key']}={p.get('value', '')}"
                for p in params if not p.get("disabled")
            )
            body_type = "x-www-form-urlencoded"
        elif mode == "formdata":
            body_type = "form-data"

    # Auth
    auth = _convert_auth(r.get("auth"))

    # Scripts
    pre_script = None
    test_script = None
    for event in item.get("event", []):
        js_code = "\n".join(event.get("script", {}).get("exec", []))
        if not js_code.strip():
            continue
        comment = f"# Converted from Postman JS (manual review needed):\n# {js_code}"
        if event.get("listen") == "prerequest":
            pre_script = comment
        elif event.get("listen") == "test":
            test_script = comment

    return ImportedRequest(
        id=generate_uuid(),
        name=item.get("name", "Request"),
        method=r.get("method", "GET"),
        url=url,
        folder_id=folder_id,
        headers=headers,
        body=body,
        body_type=body_type,
        auth=auth,
        pre_request_script=pre_script,
        test_script=test_script,
    )


def _convert_auth(auth_obj: dict | None) -> dict:
    """Convert Postman auth block to Pechkin format."""
    if not auth_obj:
        return {"type": "none"}

    auth_type = auth_obj.get("type", "noauth")

    if auth_type == "bearer":
        bearer = {i["key"]: i["value"] for i in auth_obj.get("bearer", [])}
        return {"type": "bearer", "token": bearer.get("token", "")}

    if auth_type == "basic":
        basic = {i["key"]: i["value"] for i in auth_obj.get("basic", [])}
        return {
            "type": "basic",
            "username": basic.get("username", ""),
            "password": basic.get("password", ""),
        }

    if auth_type == "apikey":
        apikey = {i["key"]: i["value"] for i in auth_obj.get("apikey", [])}
        return {
            "type": "api_key",
            "key": apikey.get("key", ""),
            "value": apikey.get("value", ""),
            "in": apikey.get("in", "header"),
        }

    return {"type": "none"}
