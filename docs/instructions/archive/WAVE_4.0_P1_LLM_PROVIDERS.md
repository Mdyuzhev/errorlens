# Wave 4.0 P1: LLM Providers

## Scope

Create 6 files in `backend/app/providers/`:
- `base.py`
- `anthropic.py`
- `openai.py`
- `gigachat.py`
- `factory.py`
- `rate_limiter.py`

## Interfaces

### base.py

```python
class LLMProviderError(Exception):
    def __init__(self, provider: str, message: str, status_code: int | None = None): ...

class BaseLLMProvider(ABC):
    base_url: str
    default_timeout: int = 120
    
    async def _request(self, endpoint: str, payload: dict, headers: dict) -> dict:
        """Shared HTTP logic. Implement once, reuse in all providers."""
        ...
    
    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str: ...
    
    @abstractmethod
    def get_model_name(self) -> str: ...
```

### Architecture Note
All providers inherit `_request()` from base. No duplicate HTTP client code.

### anthropic.py

```python
class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"): ...
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str: ...
    def get_model_name(self) -> str: ...
```

### openai.py

```python
class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"): ...
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str: ...
    def get_model_name(self) -> str: ...
```

### gigachat.py

```python
class GigaChatProvider(BaseLLMProvider):
    def __init__(self, credentials: str, model: str = "GigaChat"): ...
    async def _get_token(self) -> str: ...
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str: ...
    def get_model_name(self) -> str: ...
```

### factory.py

```python
ProviderType = Literal["anthropic", "openai", "gigachat", "groq", "gemini", "ollama"]

class ProviderFactory:
    @classmethod
    def create(cls, provider_type: ProviderType, api_key: str | None = None, model: str | None = None) -> BaseLLMProvider: ...
    
    @classmethod
    def list_providers(cls) -> list[str]: ...
```

### rate_limiter.py

```python
class RateLimiter:
    def __init__(self, provider: str): ...
    async def acquire(self) -> None: ...
    def estimate_wait_time(self) -> float: ...

def get_rate_limiter(provider: str) -> RateLimiter: ...
```

## Requirements

### HTTP Client
- Use `httpx.AsyncClient`
- Timeout: 120s
- Reuse client within request (context manager)

### Rate Limits

| Provider | RPM | TPM |
|----------|-----|-----|
| anthropic | 50 | 40000 |
| openai | 60 | 90000 |
| gigachat | 30 | - |
| groq | 30 | 6000 |
| gemini | 60 | - |
| ollama | 1000 | - |

### Error Handling
- Catch `httpx.HTTPStatusError`
- Catch `httpx.TimeoutException`
- Raise custom `LLMProviderError` with details

### Memory
- Rate limiter timestamps: keep only last 60 seconds
- Cleanup on each `acquire()` call

## Prohibited

- Bare `except:`
- Global httpx client (create per request)
- Hard-coded API URLs in providers (use constants)
- Copy code between providers (use base class)

## Tests Required

```python
# tests/test_providers.py

def test_factory_list_providers(): ...
def test_factory_create_unknown_raises(): ...
def test_factory_create_ollama_no_key(): ...
def test_rate_limiter_blocks_when_full(): ...
def test_rate_limiter_cleanup_old_timestamps(): ...
def test_provider_timeout_handling(): ...
def test_provider_error_handling(): ...
```

## Config Updates

Add to `backend/app/config.py`:
```python
ANTHROPIC_API_KEY: str = ""
OPENAI_API_KEY: str = ""
GIGACHAT_CREDENTIALS: str = ""
```

## Commit

```
[Wave 4.0] P1: Add LLM providers with factory and rate limiter
```
