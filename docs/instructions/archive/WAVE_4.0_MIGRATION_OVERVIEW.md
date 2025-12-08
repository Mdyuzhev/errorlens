# Wave 4.0: Sharmanka Migration

## Execution Order

```
P1 → P2 → P3 → P4 → P5 → P6 → P7
```

## Phase Summary

| Phase | Scope | Files | Tests |
|-------|-------|-------|-------|
| P1 | LLM Providers | 6 | 7 |
| P2 | Input Parsers | 4 | 16 |
| P3 | Generator Core | 6 | 13 |
| P4 | WebSocket | 3 | 8 |
| P5 | API | 2 | 12 |
| P6 | Vue UI | 6 | 8 |
| P7 | Settings | 1 | 7 |

Total: 28 files, 71 tests

## Architecture

```
Input: HAR/Swagger
    ↓
Parser: HARInput/SwaggerInput → EndpointSpec[]
    ↓
Generator: LLMTestGenerator
    ↓
Provider: Anthropic/OpenAI/etc via Factory
    ↓
Extractor: CodeExtractor
    ↓
Validator: TestValidator
    ↓
Output: GenerationResult
```

## WebSocket Flow

```
POST /generation/from-swagger → task_id
WS /ws/generation/{task_id} → events
GET /generation/result/{result_id} → tests
GET /generation/download/{result_id} → ZIP
```

## Quality Requirements

### Memory Management
- TTL: 3600s for all caches
- Max items: 10000 per cache
- Cleanup on each operation

### Tests Per Feature
- Unit tests
- Edge cases (empty, None, duplicates)
- Error handling
- Concurrency
- Memory leaks

### Code Standards
- Type hints everywhere
- Async for I/O
- Max 500 LOC per file
- No bare except

## Instruction Format

Each phase instruction contains:
- Interface signatures (implement independently)
- Requirements list
- Prohibited patterns
- Required tests

Instructions do NOT contain full implementations.
Agent writes code independently.
