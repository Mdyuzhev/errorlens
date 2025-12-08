"""LLM-based test generator."""
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from app.providers import ProviderFactory, get_rate_limiter
from app.generators.inputs import TestGeneratorInput, EndpointSpec
from app.generators.prompts import PromptBuilder
from app.generators.utils import CodeExtractor, TestValidator, get_language_for_framework


@dataclass
class GeneratedTest:
    endpoint: str
    code: str
    is_valid: bool
    validation_error: str = ""


@dataclass
class GenerationResult:
    tests: list[GeneratedTest] = field(default_factory=list)
    conftest: str | None = None
    total_endpoints: int = 0
    successful: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


ProgressCallback = Callable[[int, int, str, str | None], Awaitable[None]]


class LLMTestGenerator:
    def __init__(self, provider: str = "anthropic", model: str | None = None,
                 framework: str = "pytest", api_key: str | None = None):
        self.provider = ProviderFactory.create(provider, api_key=api_key, model=model)
        self.framework = framework
        self.rate_limiter = get_rate_limiter(provider)
        model_name = self.provider.get_model_name().lower()
        model_size = "7b" if any(s in model_name for s in ["3b", "7b"]) else "cloud"
        self.prompt_builder = PromptBuilder(framework, model_size)
        self.code_extractor = CodeExtractor(get_language_for_framework(framework))
        self.validator = TestValidator(get_language_for_framework(framework))

    async def generate(self, input_source: TestGeneratorInput,
                       progress_callback: ProgressCallback | None = None) -> GenerationResult:
        endpoints = input_source.to_endpoints()
        result = GenerationResult(total_endpoints=len(endpoints))

        for i, endpoint in enumerate(endpoints):
            endpoint_name = f"{endpoint.method} {endpoint.path}"
            if progress_callback:
                await progress_callback(i + 1, len(endpoints), endpoint_name, f"Generating {endpoint_name}...")

            try:
                await self.rate_limiter.acquire()
                test = await self._generate_single(endpoint)
                result.tests.append(test)
                if test.is_valid:
                    result.successful += 1
                else:
                    result.failed += 1
                    result.errors.append(f"{endpoint_name}: {test.validation_error}")
            except Exception as e:
                result.failed += 1
                result.errors.append(f"{endpoint_name}: {e}")
                result.tests.append(GeneratedTest(endpoint_name, "", False, str(e)))

        if self.framework == "pytest" and result.successful > 0:
            result.conftest = self._generate_conftest(input_source)
        return result

    async def _generate_single(self, endpoint: EndpointSpec) -> GeneratedTest:
        prompt = self.prompt_builder.build_prompt(
            endpoint.method, endpoint.path, endpoint.parameters, endpoint.request_body)
        raw = await self.provider.generate(prompt)
        code = self.code_extractor.extract(raw)
        is_valid, error = self.validator.validate(code)
        return GeneratedTest(f"{endpoint.method} {endpoint.path}", code, is_valid, error)

    def _generate_conftest(self, input_source: TestGeneratorInput) -> str:
        base_url = input_source.get_base_url()
        return f'''import pytest
import requests

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{{self.base_url}}{{path}}"
        if self.token:
            kwargs.setdefault("headers", {{}})
            kwargs["headers"]["Authorization"] = f"Bearer {{self.token}}"
        return self.session.request(method, url, **kwargs)

@pytest.fixture
def api_client():
    return APIClient("{base_url}")
'''
