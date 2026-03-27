"""OpenAPI spec parser — port of Pe4King parser.ts + ref-resolver.ts + schema-visitor.ts."""

import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
import yaml


@dataclass
class SchemaField:
    name: str
    path: str           # JSON path: "user.email", "items[0].id"
    field_type: str     # string, integer, number, boolean, array, object
    format: str | None = None
    required: bool = False
    nullable: bool = False
    enum_values: list[str] | None = None
    description: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    min_items: int | None = None
    max_items: int | None = None
    example: Any = None


@dataclass
class ParameterInfo:
    name: str
    param_in: str       # path, query, header, formData
    required: bool
    schema: SchemaField
    example: Any = None


@dataclass
class EndpointInfo:
    method: str         # GET, POST, PUT, PATCH, DELETE
    path: str
    operation_id: str | None = None
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    path_params: list[ParameterInfo] = field(default_factory=list)
    query_params: list[ParameterInfo] = field(default_factory=list)
    request_body_schema: list[SchemaField] = field(default_factory=list)
    request_body_required: bool = False
    success_status: int = 200
    response_fields: list[SchemaField] = field(default_factory=list)
    has_response_schema: bool = False
    has_security: bool = False


@dataclass
class ParsedSpec:
    title: str
    version: str
    base_url: str
    endpoints: list[EndpointInfo]


class OpenAPISpecParser:
    def __init__(self, spec: str | dict):
        self._raw = self._load(spec)
        self._is_swagger2 = str(self._raw.get("swagger", "")).startswith("2")
        self._ref_cache: dict[str, dict] = {}

    def parse(self) -> ParsedSpec:
        info = self._raw.get("info", {})
        return ParsedSpec(
            title=info.get("title", "API"),
            version=info.get("version", "1.0.0"),
            base_url=self._extract_base_url(),
            endpoints=self._parse_endpoints(),
        )

    @classmethod
    def from_url(cls, url: str) -> "OpenAPISpecParser":
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        content = resp.text
        try:
            return cls(json.loads(content))
        except json.JSONDecodeError:
            return cls(yaml.safe_load(content))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self, spec: str | dict) -> dict:
        if isinstance(spec, dict):
            return spec
        if isinstance(spec, str):
            text = spec.strip()
            if text.startswith("{") or text.startswith("["):
                try:
                    result = json.loads(text)
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    pass
            result = yaml.safe_load(text)
            if result is None or not isinstance(result, dict):
                raise ValueError("Invalid OpenAPI spec")
            return result
        raise ValueError("Invalid OpenAPI spec")

    def _resolve(self, obj: Any) -> Any:
        if not isinstance(obj, dict):
            return obj
        ref = obj.get("$ref")
        if ref is None:
            return obj
        if ref in self._ref_cache:
            return self._ref_cache[ref]
        # Prevent infinite recursion: put a placeholder
        self._ref_cache[ref] = {}
        parts = ref.lstrip("#/").split("/")
        node = self._raw
        for part in parts:
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict):
                node = node.get(part, {})
            else:
                node = {}
        resolved = self._resolve(node) if isinstance(node, dict) else node
        if isinstance(resolved, dict):
            self._ref_cache[ref] = resolved
        return resolved

    def _extract_base_url(self) -> str:
        if self._is_swagger2:
            schemes = self._raw.get("schemes", ["https"])
            host = self._raw.get("host", "localhost")
            base_path = self._raw.get("basePath", "")
            return f"{schemes[0]}://{host}{base_path}"
        servers = self._raw.get("servers", [])
        if servers and isinstance(servers, list) and servers[0].get("url"):
            return servers[0]["url"]
        return "http://localhost:8080"

    def _parse_endpoints(self) -> list[EndpointInfo]:
        endpoints: list[EndpointInfo] = []
        paths = self._raw.get("paths", {})
        if not isinstance(paths, dict):
            return endpoints
        methods = {"get", "post", "put", "patch", "delete"}
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            path_item = self._resolve(path_item)
            for method in methods:
                operation = path_item.get(method)
                if operation is None:
                    continue
                operation = self._resolve(operation)
                endpoints.append(
                    self._parse_operation(path, method, operation, path_item)
                )
        return endpoints

    def _parse_operation(
        self,
        path: str,
        method: str,
        operation: dict,
        path_item: dict,
    ) -> EndpointInfo:
        # Merge path-level and operation-level parameters
        raw_params = list(path_item.get("parameters", []))
        raw_params.extend(operation.get("parameters", []))

        path_params: list[ParameterInfo] = []
        query_params: list[ParameterInfo] = []
        request_body_schema: list[SchemaField] = []
        request_body_required = False

        for raw_p in raw_params:
            raw_p = self._resolve(raw_p)
            if not isinstance(raw_p, dict):
                continue
            p_in = raw_p.get("in", "")

            if self._is_swagger2 and p_in == "body":
                body_schema = self._resolve(raw_p.get("schema", {}))
                request_body_schema = self._visit_schema(body_schema)
                request_body_required = raw_p.get("required", False)
                continue

            if self._is_swagger2 and p_in == "formData":
                sf = self._schema_field_from_param(raw_p, raw_p.get("name", ""))
                request_body_schema.append(sf)
                continue

            param_info = self._parse_parameter(raw_p)
            if p_in == "path":
                path_params.append(param_info)
            elif p_in == "query":
                query_params.append(param_info)

        # OpenAPI 3.x requestBody
        if not self._is_swagger2:
            req_body = operation.get("requestBody")
            if req_body:
                req_body = self._resolve(req_body)
                request_body_required = req_body.get("required", False)
                content = req_body.get("content", {})
                json_content = content.get("application/json", {})
                body_schema = self._resolve(json_content.get("schema", {}))
                if body_schema:
                    request_body_schema = self._visit_schema(body_schema)

        # Responses
        responses = operation.get("responses", {})
        success_status, resp_schema = self._get_success_response(responses)
        response_fields: list[SchemaField] = []
        has_response_schema = False
        if resp_schema:
            has_response_schema = True
            response_fields = self._visit_schema(resp_schema)

        has_security = bool(
            operation.get("security") or self._raw.get("security")
        )

        return EndpointInfo(
            method=method.upper(),
            path=path,
            operation_id=operation.get("operationId"),
            summary=operation.get("summary"),
            tags=operation.get("tags", []),
            path_params=path_params,
            query_params=query_params,
            request_body_schema=request_body_schema,
            request_body_required=request_body_required,
            success_status=success_status,
            response_fields=response_fields,
            has_response_schema=has_response_schema,
            has_security=has_security,
        )

    def _parse_parameter(self, param: dict) -> ParameterInfo:
        param = self._resolve(param)
        name = param.get("name", "")
        p_in = param.get("in", "")
        required = param.get("required", False)
        example = param.get("example")

        schema_raw = param.get("schema")
        if schema_raw:
            schema_raw = self._resolve(schema_raw)
        else:
            # Swagger 2.0: schema info is inline in the parameter
            schema_raw = {
                k: v
                for k, v in param.items()
                if k in (
                    "type", "format", "enum", "minimum", "maximum",
                    "minLength", "maxLength", "pattern", "description",
                    "example", "default",
                )
            }

        sf = self._schema_field_from_param(schema_raw, name)
        sf.required = required

        return ParameterInfo(
            name=name,
            param_in=p_in,
            required=required,
            schema=sf,
            example=example,
        )

    def _schema_field_from_param(self, schema: dict, name: str) -> SchemaField:
        return SchemaField(
            name=name,
            path=name,
            field_type=schema.get("type", "string"),
            format=schema.get("format"),
            nullable=schema.get("nullable", False),
            enum_values=schema.get("enum"),
            description=schema.get("description"),
            minimum=schema.get("minimum"),
            maximum=schema.get("maximum"),
            min_length=schema.get("minLength"),
            max_length=schema.get("maxLength"),
            pattern=schema.get("pattern"),
            min_items=schema.get("minItems"),
            max_items=schema.get("maxItems"),
            example=schema.get("example"),
        )

    def _visit_schema(
        self,
        schema: dict | None,
        path: str = "",
        required_fields: set[str] | None = None,
        depth: int = 0,
    ) -> list[SchemaField]:
        if depth > 4 or not schema:
            return []

        schema = self._resolve(schema)
        if not isinstance(schema, dict):
            return []

        schema_type = schema.get("type", "")

        # allOf / anyOf / oneOf
        for combo_key in ("allOf", "anyOf", "oneOf"):
            combo = schema.get(combo_key)
            if combo and isinstance(combo, list):
                fields: list[SchemaField] = []
                # Collect required from all sub-schemas + parent
                merged_required: set[str] = set(schema.get("required", []))
                for sub in combo:
                    sub = self._resolve(sub)
                    if isinstance(sub, dict):
                        merged_required.update(sub.get("required", []))
                for sub in combo:
                    sub = self._resolve(sub)
                    if isinstance(sub, dict):
                        fields.extend(
                            self._visit_schema(
                                sub, path, merged_required, depth + 1,
                            )
                        )
                return fields

        if schema_type == "object" or "properties" in schema:
            req = set(schema.get("required", []))
            if required_fields is not None:
                req = required_fields
            props = schema.get("properties", {})
            fields = []
            for prop_name, prop_schema in props.items():
                child_path = f"{path}.{prop_name}" if path else prop_name
                prop_schema = self._resolve(prop_schema)
                if not isinstance(prop_schema, dict):
                    continue
                child_type = prop_schema.get("type", "object")

                # If it's a nested object or has $ref, recurse
                if (
                    child_type == "object"
                    or "properties" in prop_schema
                    or "$ref" in prop_schema
                ):
                    # Add the object field itself
                    fields.append(
                        SchemaField(
                            name=prop_name,
                            path=child_path,
                            field_type="object",
                            format=prop_schema.get("format"),
                            required=prop_name in req,
                            nullable=prop_schema.get("nullable", False),
                            description=prop_schema.get("description"),
                            example=prop_schema.get("example"),
                        )
                    )
                    fields.extend(
                        self._visit_schema(
                            prop_schema, child_path, None, depth + 1,
                        )
                    )
                elif child_type == "array":
                    fields.append(
                        SchemaField(
                            name=prop_name,
                            path=child_path,
                            field_type="array",
                            format=prop_schema.get("format"),
                            required=prop_name in req,
                            nullable=prop_schema.get("nullable", False),
                            description=prop_schema.get("description"),
                            min_items=prop_schema.get("minItems"),
                            max_items=prop_schema.get("maxItems"),
                            example=prop_schema.get("example"),
                        )
                    )
                    items = prop_schema.get("items")
                    if items:
                        fields.extend(
                            self._visit_schema(
                                items,
                                f"{child_path}[0]",
                                None,
                                depth + 1,
                            )
                        )
                else:
                    fields.append(
                        SchemaField(
                            name=prop_name,
                            path=child_path,
                            field_type=child_type,
                            format=prop_schema.get("format"),
                            required=prop_name in req,
                            nullable=prop_schema.get("nullable", False),
                            enum_values=prop_schema.get("enum"),
                            description=prop_schema.get("description"),
                            minimum=prop_schema.get("minimum"),
                            maximum=prop_schema.get("maximum"),
                            min_length=prop_schema.get("minLength"),
                            max_length=prop_schema.get("maxLength"),
                            pattern=prop_schema.get("pattern"),
                            min_items=prop_schema.get("minItems"),
                            max_items=prop_schema.get("maxItems"),
                            example=prop_schema.get("example"),
                        )
                    )
            return fields

        if schema_type == "array":
            fields = []
            items = schema.get("items")
            if items:
                fields = self._visit_schema(
                    items, f"{path}[0]" if path else "[0]", None, depth + 1,
                )
            return fields

        # Primitive type
        name = path.rsplit(".", 1)[-1] if "." in path else path
        name = re.sub(r"\[\d+\]$", "", name)
        if not name:
            name = schema_type
        return [
            SchemaField(
                name=name,
                path=path or name,
                field_type=schema_type or "string",
                format=schema.get("format"),
                required=False,
                nullable=schema.get("nullable", False),
                enum_values=schema.get("enum"),
                description=schema.get("description"),
                minimum=schema.get("minimum"),
                maximum=schema.get("maximum"),
                min_length=schema.get("minLength"),
                max_length=schema.get("maxLength"),
                pattern=schema.get("pattern"),
                example=schema.get("example"),
            )
        ]

    def _get_success_response(
        self, responses: dict,
    ) -> tuple[int, dict | None]:
        if not isinstance(responses, dict):
            return 200, None
        for code in (200, 201, 202, 204):
            str_code = str(code)
            resp = responses.get(str_code) or responses.get(code)
            if resp is None:
                continue
            resp = self._resolve(resp)
            if not isinstance(resp, dict):
                continue
            if self._is_swagger2:
                schema = resp.get("schema")
                if schema:
                    return code, self._resolve(schema)
                return code, None
            # OpenAPI 3.x
            content = resp.get("content", {})
            json_content = content.get("application/json", {})
            schema = json_content.get("schema")
            if schema:
                return code, self._resolve(schema)
            return code, None
        return 200, None
