"""Tests for Wave 4.0 input parsers."""

import pytest
from app.generators.inputs import HARInput, SwaggerInput, SwaggerValidationError


def test_har_parse():
    """Test HAR parsing from list format."""
    har = [{"request": {"url": "https://api.test.com/users", "method": "GET", "headers": []}}]
    parser = HARInput(har)
    endpoints = parser.to_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0].path == "/users"
    assert endpoints[0].method == "GET"


def test_har_parse_with_log():
    """Test HAR parsing from HAR log format."""
    har = {"log": {"entries": [{"request": {"url": "https://api.test.com/posts", "method": "POST", "headers": []}}]}}
    parser = HARInput(har)
    endpoints = parser.to_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0].path == "/posts"
    assert endpoints[0].method == "POST"


def test_har_base_url():
    """Test base URL extraction from HAR."""
    har = [{"request": {"url": "https://api.example.com/v1/users", "method": "GET", "headers": []}}]
    parser = HARInput(har)
    assert parser.get_base_url() == "https://api.example.com"


def test_swagger_parse():
    """Test Swagger/OpenAPI parsing."""
    spec = {"openapi": "3.0.0", "paths": {"/users": {"get": {"responses": {"200": {}}}}}}
    parser = SwaggerInput(spec)
    endpoints = parser.to_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0].method == "GET"
    assert endpoints[0].path == "/users"


def test_swagger_validation_error():
    """Test Swagger validation raises on invalid spec."""
    with pytest.raises(SwaggerValidationError, match="Missing openapi/swagger version"):
        SwaggerInput({"paths": {}})


def test_swagger_missing_paths():
    """Test Swagger validation raises on missing paths."""
    with pytest.raises(SwaggerValidationError, match="Missing paths field"):
        SwaggerInput({"openapi": "3.0.0"})


def test_swagger_base_url_from_servers():
    """Test base URL extraction from OpenAPI servers."""
    spec = {
        "openapi": "3.0.0",
        "servers": [{"url": "https://api.prod.com"}],
        "paths": {"/test": {"get": {}}}
    }
    parser = SwaggerInput(spec)
    assert parser.get_base_url() == "https://api.prod.com"


def test_swagger_base_url_from_host():
    """Test base URL extraction from Swagger 2.0 host."""
    spec = {
        "swagger": "2.0",
        "host": "api.example.com",
        "basePath": "/v1",
        "paths": {"/test": {"get": {}}}
    }
    parser = SwaggerInput(spec)
    assert parser.get_base_url() == "https://api.example.com/v1"
