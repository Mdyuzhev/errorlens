# Contributing to ErrorLens

First off, thanks for taking the time to contribute! 🎉

## How Can I Contribute?

### Reporting Bugs

- Check if the bug has already been reported in [Issues](https://github.com/Mdyuzhev/errorlens/issues)
- If not, create a new issue with a clear title and description
- Include steps to reproduce, expected behavior, and actual behavior
- Add screenshots or console output if relevant

### Suggesting Features

- Open an issue with the `enhancement` label
- Describe the feature and why it would be useful
- Be open to discussion about implementation details

### Pull Requests

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Python: Follow PEP 8, use type hints
- JavaScript: Use modern ES6+ syntax, keep it vanilla (no frameworks)
- Keep functions small and focused
- Write meaningful commit messages

## Commit Message Guidelines (QA Integration)

Our QA team uses AI-powered test generation that parses commit messages and docstrings. To help the AI generate better tests, follow these guidelines:

### Good Commit Messages

Include context about what the endpoint/function does:

```
Add GET /projects/{id}/sessions endpoint

Returns all sessions belonging to project. Requires owner/admin/member
permissions — viewers get 403. Supports pagination via limit/offset with
default limit=20, max=100. Returns 404 if project not found or user
has no access.

Response includes session metadata but not full captured data.
```

### Poor Commit Messages (avoid)

```
fix bug
add endpoint
update code
```

### Docstrings for Endpoints

Always include docstrings that explain:
- What the endpoint does
- Required permissions
- Important edge cases
- Response format

Example:
```python
@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete session and all related data (captured events, analysis).

    Requires member role or higher. Viewers get 403.
    Returns 404 if session not found or belongs to different project.
    Cascade deletes session_data and analysis_result tables.
    """
```

### What the AI Generates

From good commit messages and docstrings, the AI will generate:
- Auth/permission tests (403 for unauthorized roles)
- Validation tests (400 for invalid input)
- Not found tests (404 scenarios)
- Pagination edge cases
- Response schema validation

### When to Write Tests Manually

Write tests manually for:
- Complex business logic
- Non-obvious permission rules
- Integration between multiple services
- Race conditions and concurrency

## Development Setup

See [README.md](README.md) for local development instructions.

## Questions?

Feel free to open an issue with the `question` label or start a discussion.
