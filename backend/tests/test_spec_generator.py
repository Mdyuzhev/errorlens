"""Tests for spec test generator."""

import json
import pytest
from app.generators.spec_parser import EndpointInfo, SchemaField, ParameterInfo
from app.generators.spec_generator import SpecTestGenerator, GeneratorConfig


def make_endpoint(
    method="GET", path="/pets", summary="List pets", tags=None,
    request_body_schema=None, request_body_required=False,
    response_fields=None, success_status=200, has_response_schema=False,
    path_params=None, query_params=None,
):
    return EndpointInfo(
        method=method, path=path, summary=summary,
        tags=tags or ["pets"],
        request_body_schema=request_body_schema or [],
        request_body_required=request_body_required,
        response_fields=response_fields or [],
        success_status=success_status,
        has_response_schema=has_response_schema,
        path_params=path_params or [],
        query_params=query_params or [],
    )


class TestSpecGenerator:
    def test_pytest_generation(self):
        ep = make_endpoint(
            method="POST", path="/users",
            request_body_schema=[
                SchemaField(
                    name="email", path="email", field_type="string",
                    format="email", required=True,
                ),
                SchemaField(
                    name="name", path="name", field_type="string",
                    required=True,
                ),
            ],
            request_body_required=True, success_status=201,
        )

        config = GeneratorConfig(
            framework="pytest", base_url="http://localhost:8000",
        )
        result = SpecTestGenerator().generate([ep], config)
        assert result.success
        assert len(result.files) >= 2
        test_file = next(f for f in result.files if f.filename == "test_api.py")
        assert "def test_" in test_file.content
        assert "assert" in test_file.content

    def test_enum_assertion(self):
        ep = make_endpoint(
            response_fields=[
                SchemaField(
                    name="status", path="status", field_type="string",
                    enum_values=["active", "inactive"],
                ),
            ],
            has_response_schema=True,
        )
        config = GeneratorConfig(framework="pytest")
        result = SpecTestGenerator().generate([ep], config)
        test_file = next(f for f in result.files if f.filename == "test_api.py")
        assert "in [" in test_file.content or "in (" in test_file.content

    def test_datetime_assertion(self):
        ep = make_endpoint(
            response_fields=[
                SchemaField(
                    name="created_at", path="created_at",
                    field_type="string", format="date-time",
                ),
            ],
            has_response_schema=True,
        )
        config = GeneratorConfig(framework="pytest")
        result = SpecTestGenerator().generate([ep], config)
        test_file = next(f for f in result.files if f.filename == "test_api.py")
        assert "re.match" in test_file.content

    def test_negative_tests_with_minimum(self):
        ep = make_endpoint(
            method="POST", path="/items",
            request_body_schema=[
                SchemaField(
                    name="price", path="price", field_type="number",
                    minimum=0, required=True,
                ),
            ],
            request_body_required=True, success_status=201,
        )
        config = GeneratorConfig(
            framework="pytest", generate_negative_tests=True,
        )
        result = SpecTestGenerator().generate([ep], config)
        test_file = next(f for f in result.files if f.filename == "test_api.py")
        assert "400" in test_file.content or "422" in test_file.content
        assert result.stats.negative_tests > 0

    def test_postman_generation(self):
        ep = make_endpoint()
        config = GeneratorConfig(
            framework="postman", base_url="http://localhost:8000",
        )
        result = SpecTestGenerator().generate([ep], config)
        assert result.success
        coll_file = next(
            f for f in result.files if f.filename == "collection.json"
        )
        coll = json.loads(coll_file.content)
        assert "item" in coll
        assert coll_file.language == "json"

    def test_rest_assured_generation(self):
        ep = make_endpoint()
        config = GeneratorConfig(framework="rest-assured")
        result = SpecTestGenerator().generate([ep], config)
        assert result.success
        java_file = next(
            f for f in result.files if f.filename == "ApiTests.java"
        )
        assert "@Test" in java_file.content
        assert java_file.language == "java"

    def test_stats_counting(self):
        eps = [
            make_endpoint(method="GET", path="/a"),
            make_endpoint(
                method="POST", path="/b",
                request_body_schema=[
                    SchemaField(
                        name="x", path="x", field_type="string",
                        required=True,
                    ),
                ],
                request_body_required=True, success_status=201,
            ),
        ]
        config = GeneratorConfig(
            framework="pytest", generate_negative_tests=True,
        )
        result = SpecTestGenerator().generate(eps, config)
        assert result.stats.total_endpoints == 2
        assert result.stats.total_tests > 0
        assert result.stats.positive_tests > 0
