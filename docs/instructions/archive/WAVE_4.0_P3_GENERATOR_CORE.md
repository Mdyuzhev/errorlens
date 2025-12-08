# Wave 4.0 P3: Generator Core

## Scope

Create files in `backend/app/generators/`:
- `prompts/__init__.py`
- `prompts/prompt_builder.py`
- `utils/__init__.py`
- `utils/code_extractor.py`
- `utils/test_validator.py`
- `llm_generator.py`

## Interfaces

### prompts/prompt_builder.py

```python
class PromptBuilder:
    def __init__(self, framework: str = "pytest", model_size: str = "cloud"): ...
    
    def build_prompt(
        self,
        method: str,
        path: str,
        parameters: dict | None = None,
        request_body: dict | None = None,
        responses: dict | None = None
    ) -> str: ...
```

### utils/code_extractor.py

```python
def get_language_for_framework(framework: str) -> str: ...

class CodeExtractor:
    def __init__(self, language: str = "python"): ...
    def extract(self, text: str) -> str: ...
```

### utils/test_validator.py

```python
class TestValidator:
    def __init__(self, language: str = "python"): ...
    def validate(self, code: str) -> tuple[bool, str]: ...

def validate_pytest_syntax(code: str) -> bool: ...
```

### llm_generator.py

```python
@dataclass
class GeneratedTest:
    endpoint: str
    code: str
    is_valid: bool
    validation_error: str = ""
    created_at: float = field(default_factory=time.time)

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
    def __init__(
        self,
        provider: str = "anthropic",
        model: str | None = None,
        framework: str = "pytest",
        api_key: str | None = None
    ): ...
    
    async def generate(
        self,
        input_source: TestGeneratorInput,
        progress_callback: ProgressCallback | None = None
    ) -> GenerationResult: ...
```

## Requirements

### PromptBuilder
- Adapt prompt complexity to model_size: "3b", "7b", "14b", "cloud"
- Smaller models: shorter prompts, explicit constraints
- Include one example per HTTP method
- Output format instructions at end

### CodeExtractor
- Extract from markdown code blocks (```python, ```)
- Extract from raw text (find import/def patterns)
- Remove LLM artifacts: "Here is", "This code", etc.
- Handle mixed text and code

### TestValidator
- Python: use `ast.parse()`, return syntax error details
- Java: check brace matching, @Test presence
- JavaScript: check brace matching

### LLMGenerator
- Rate limit before each LLM call
- Progress callback after each endpoint
- Generate conftest.py for pytest framework
- Handle provider errors gracefully

## Prohibited

- Bare `except:`
- Infinite retries
- Blocking I/O
- Prompts over 2000 tokens for small models

## Tests Required

```python
# tests/test_generator_core.py

def test_prompt_builder_cloud_model(): ...
def test_prompt_builder_small_model(): ...
def test_prompt_builder_all_http_methods(): ...

def test_code_extractor_markdown(): ...
def test_code_extractor_raw_text(): ...
def test_code_extractor_mixed_content(): ...
def test_code_extractor_empty_input(): ...

def test_validator_valid_python(): ...
def test_validator_invalid_python(): ...
def test_validator_java_braces(): ...

def test_generator_single_endpoint(): ...
def test_generator_multiple_endpoints(): ...
def test_generator_progress_callback(): ...
def test_generator_provider_error(): ...
def test_generator_conftest_generated(): ...
```

## Commit

```
[Wave 4.0] P3: Add LLMTestGenerator with prompts and validators
```
