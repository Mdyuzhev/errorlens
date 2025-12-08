# Wave 4.0 P2: Input Parsers

## Scope

Create 4 files in `backend/app/generators/inputs/`:
- `__init__.py`
- `base.py`
- `har_input.py`
- `swagger_input.py`

## Interfaces

### base.py

```python
@dataclass
class EndpointSpec:
    method: str
    path: str
    parameters: dict | None = None
    request_body: dict | None = None
    response_schema: dict | None = None
    headers: dict = field(default_factory=dict)
    auth_type: str | None = None
    description: str = ""

class TestGeneratorInput(ABC):
    @abstractmethod
    def to_endpoints(self) -> list[EndpointSpec]: ...
    
    @abstractmethod
    def get_base_url(self) -> str: ...
    
    @abstractmethod
    def get_auth_config(self) -> dict | None: ...
```

### har_input.py

```python
class HARInput(TestGeneratorInput):
    def __init__(self, har_data: dict | list): ...
    def to_endpoints(self) -> list[EndpointSpec]: ...
    def get_base_url(self) -> str: ...
    def get_auth_config(self) -> dict | None: ...
```

### swagger_input.py

```python
class SwaggerValidationError(Exception): ...

class SwaggerInput(TestGeneratorInput):
    def __init__(self, spec: dict | str | Path): ...
    def to_endpoints(self) -> list[EndpointSpec]: ...
    def get_base_url(self) -> str: ...
    def get_auth_config(self) -> dict | None: ...
```

## Requirements

### HAR Parser
- Accept standard HAR format (`{"log": {"entries": [...]}}`)
- Accept list of RecordedHttpExchange dicts
- Extract: method, path, headers, body, query params
- Detect auth type from headers: bearer, basic, api_key

### Swagger Parser
- Accept OpenAPI 3.x and Swagger 2.x
- Accept JSON and YAML formats
- Resolve `$ref` references (single level)
- Extract: method, path, parameters, requestBody, responses
- Handle `servers` (OpenAPI 3) and `host/basePath` (Swagger 2)

### Validation
- SwaggerInput: raise `SwaggerValidationError` if missing `paths`
- HARInput: skip malformed entries, don't fail

### Deduplication
- Remove duplicate endpoints (same method + path)
- Keep first occurrence

## Prohibited

- Recursive $ref resolution (single level only)
- Bare `except:`
- Silent failures in Swagger parsing

## Tests Required

```python
# tests/test_input_parsers.py

def test_har_standard_format(): ...
def test_har_recorded_exchange_format(): ...
def test_har_empty_entries(): ...
def test_har_malformed_entry_skipped(): ...
def test_har_duplicate_endpoints(): ...
def test_har_auth_detection_bearer(): ...
def test_har_auth_detection_basic(): ...
def test_har_auth_detection_api_key(): ...

def test_swagger_openapi3(): ...
def test_swagger_v2(): ...
def test_swagger_yaml_format(): ...
def test_swagger_missing_paths_raises(): ...
def test_swagger_ref_resolution(): ...
def test_swagger_deep_refs_single_level(): ...
def test_swagger_base_url_servers(): ...
def test_swagger_base_url_host(): ...
```

## Commit

```
[Wave 4.0] P2: Add HAR and Swagger input parsers
```
