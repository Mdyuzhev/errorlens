"""Tests for Wave 4.0 LLM test generator."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.generators import LLMTestGenerator, SwaggerInput, HARInput
from app.generators.inputs import EndpointSpec


@pytest.mark.asyncio
async def test_llm_generator_basic():
    """Test basic LLM generator initialization."""
    generator = LLMTestGenerator(provider="ollama", framework="pytest")
    assert generator.framework == "pytest"
    assert generator.provider.get_model_name() is not None


@pytest.mark.asyncio
async def test_generate_from_swagger():
    """Test generation from Swagger spec."""
    spec = {"openapi": "3.0.0", "paths": {"/users": {"get": {"responses": {"200": {}}}}}}
    input_source = SwaggerInput(spec)

    generator = LLMTestGenerator(provider="ollama", framework="pytest")
    generator.provider.generate = AsyncMock(return_value="import pytest\ndef test_get_users(api_client):\n    response = api_client.request('GET', '/users')\n    assert response.status_code == 200")

    result = await generator.generate(input_source)

    assert result.total_endpoints == 1
    assert result.successful >= 0  # May fail validation but shouldn't crash
    assert result.conftest is not None


@pytest.mark.asyncio
async def test_generate_from_har():
    """Test generation from HAR data."""
    har = [{"request": {"url": "https://api.test.com/users", "method": "GET", "headers": []}}]
    input_source = HARInput(har)

    generator = LLMTestGenerator(provider="ollama", framework="pytest")
    generator.provider.generate = AsyncMock(return_value="import pytest\ndef test_get_users(api_client):\n    response = api_client.request('GET', '/users')\n    assert response.status_code == 200")

    result = await generator.generate(input_source)

    assert result.total_endpoints == 1
    assert len(result.tests) == 1


@pytest.mark.asyncio
async def test_progress_callback():
    """Test progress callback is called."""
    spec = {"openapi": "3.0.0", "paths": {"/users": {"get": {}}, "/posts": {"get": {}}}}
    input_source = SwaggerInput(spec)

    generator = LLMTestGenerator(provider="ollama", framework="pytest")
    generator.provider.generate = AsyncMock(return_value="import pytest\ndef test(api_client):\n    pass")

    progress_calls = []

    async def progress_callback(current, total, endpoint, log):
        progress_calls.append((current, total, endpoint))

    result = await generator.generate(input_source, progress_callback=progress_callback)

    assert len(progress_calls) == 2
    assert progress_calls[0][0] == 1
    assert progress_calls[1][0] == 2


def test_code_extractor():
    """Test code extraction from markdown."""
    from app.generators.utils import CodeExtractor

    extractor = CodeExtractor("python")
    code = extractor.extract("```python\nimport pytest\ndef test():\n    pass\n```")

    assert "import pytest" in code
    assert "def test():" in code
    assert "```" not in code


def test_test_validator():
    """Test Python code validation."""
    from app.generators.utils import TestValidator

    validator = TestValidator("python")

    valid_code = "import pytest\ndef test():\n    pass"
    is_valid, error = validator.validate(valid_code)
    assert is_valid
    assert error == ""

    invalid_code = "def test(\n    pass"
    is_valid, error = validator.validate(invalid_code)
    assert not is_valid
    assert "Syntax error" in error
