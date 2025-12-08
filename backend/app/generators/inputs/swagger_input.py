"""Swagger/OpenAPI input parser."""

import json
import yaml
from pathlib import Path
from .base import TestGeneratorInput, EndpointSpec


class SwaggerValidationError(Exception):
    pass


class SwaggerInput(TestGeneratorInput):
    """Parse Swagger/OpenAPI specification."""

    def __init__(self, spec: dict | str | Path):
        self.spec = self._load_spec(spec)
        self._validate_spec()
        self._base_url = self._extract_base_url()
        self._auth_config = self._extract_auth()

    def to_endpoints(self) -> list[EndpointSpec]:
        endpoints = []
        for path, methods in self.spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    endpoints.append(self._parse_endpoint(path, method, details))
        return endpoints

    def get_base_url(self) -> str:
        return self._base_url

    def get_auth_config(self) -> dict | None:
        return self._auth_config

    def _load_spec(self, spec: dict | str | Path) -> dict:
        if isinstance(spec, dict):
            return spec
        content = spec.read_text() if isinstance(spec, Path) else spec
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return yaml.safe_load(content)

    def _validate_spec(self) -> None:
        if not isinstance(self.spec, dict):
            raise SwaggerValidationError("Spec must be a dict")
        if "openapi" not in self.spec and "swagger" not in self.spec:
            raise SwaggerValidationError("Missing openapi/swagger version")
        if "paths" not in self.spec:
            raise SwaggerValidationError("Missing paths field")

    def _extract_base_url(self) -> str:
        if "servers" in self.spec and self.spec["servers"]:
            return self.spec["servers"][0].get("url", "http://localhost")
        if "host" in self.spec:
            scheme = self.spec.get("schemes", ["https"])[0]
            return f"{scheme}://{self.spec['host']}{self.spec.get('basePath', '')}"
        return "http://localhost"

    def _extract_auth(self) -> dict | None:
        if "components" in self.spec:
            schemes = self.spec["components"].get("securitySchemes", {})
            if schemes:
                return {"schemes": schemes}
        if "securityDefinitions" in self.spec:
            return {"schemes": self.spec["securityDefinitions"]}
        return None

    def _parse_endpoint(self, path: str, method: str, details: dict) -> EndpointSpec:
        parameters = {}
        for param in details.get("parameters", []):
            if param.get("in") in ["path", "query"]:
                parameters[param.get("name", "")] = {
                    "in": param.get("in"),
                    "required": param.get("required", False),
                    "type": param.get("schema", {}).get("type", "string"),
                }

        request_body = None
        if "requestBody" in details:
            content = details["requestBody"].get("content", {})
            json_content = content.get("application/json", {})
            request_body = self._resolve_schema(json_content.get("schema", {}))

        for param in details.get("parameters", []):
            if param.get("in") == "body":
                request_body = self._resolve_schema(param.get("schema", {}))
                break

        return EndpointSpec(
            method=method.upper(),
            path=path,
            parameters=parameters if parameters else None,
            request_body=request_body,
            description=details.get("summary", "") or details.get("description", ""),
        )

    def _resolve_schema(self, schema: dict) -> dict:
        if not schema:
            return {}
        if "$ref" in schema:
            return self._get_ref(schema["$ref"])
        return schema

    def _get_ref(self, ref_path: str) -> dict:
        parts = ref_path.lstrip("#/").split("/")
        result = self.spec
        for part in parts:
            result = result.get(part, {})
        return result
