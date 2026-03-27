"""Stub — full implementation in task-01."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaField:
    name: str
    path: str
    field_type: str
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
    param_in: str
    required: bool
    schema: SchemaField
    example: Any = None


@dataclass
class EndpointInfo:
    method: str
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
    def __init__(self, spec):
        pass

    def parse(self) -> ParsedSpec:
        return ParsedSpec(title="", version="", base_url="", endpoints=[])

    @classmethod
    def from_url(cls, url: str):
        return cls({})
