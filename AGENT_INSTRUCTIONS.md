# ErrorLens — Agent Instructions

## Project Overview

ErrorLens is a lightweight open-source tool for QA engineers. It consists of a browser bookmarklet that records errors and a backend that analyzes them using AI. The goal is maximum simplicity: no registration, no browser extensions, works everywhere.

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, Pydantic
- Frontend: Vanilla JavaScript (bookmarklet)
- LLM: Google Gemini / Groq (free tier)
- Hosting: Vercel/Railway (backend), GitHub Pages (landing)
- Task Tracking: GitHub Issues + Projects

**Repository:** https://github.com/Mdyuzhev/errorlens

---

## Project Structure

```
errorlens/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI entrypoint
│   │   ├── models.py        # Pydantic schemas
│   │   ├── config.py        # Settings
│   │   ├── analyzer.py      # LLM integration (future)
│   │   └── providers/       # LLM providers (future)
│   │       ├── base.py
│   │       ├── gemini.py
│   │       └── groq.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── bookmarklet/
│   ├── recorder.js          # Main bookmarklet source
│   └── build.js             # Minification script (future)
├── landing/                  # GitHub Pages site
│   ├── index.html
│   └── style.css
├── docs/
├── .github/
│   └── workflows/           # CI/CD (future)
├── README.md
├── ROADMAP.md               # Project plan with status tracking
├── CONTRIBUTING.md
├── LICENSE
└── AGENT_INSTRUCTIONS.md    # This file
```

---

## GitHub Workflow

### Labels

| Label | Purpose |
|-------|---------|
| `epic` | Big chunk of work (contains multiple stories) |
| `story` | User story (deliverable feature) |
| `task` | Concrete implementation task |
| `phase:mvp` | Phase 1 — MVP |
| `phase:polish` | Phase 2 — Polish |
| `phase:release` | Phase 3 — Release |
| `backend` | Python/FastAPI work |
| `frontend` | JavaScript/Bookmarklet work |
| `infra` | CI/CD, deploy, configuration |

### Issue Hierarchy

- **Epic** = GitHub Issue with `epic` label, contains checklist of Stories
- **Story** = GitHub Issue with `story` label, linked to Epic via "Part of #N"
- **Task** = Checklist item inside Story, or separate Issue with `task` label for complex tasks

### Working with Issues

**Creating a Story:**
```bash
gh issue create --title "[Story 3.1] Basic FastAPI server" \
  --label "story,backend,phase:mvp" \
  --body "Part of #3

## Description
Initialize FastAPI project with basic structure.

## Tasks
- [ ] Create main.py with FastAPI app
- [ ] Add CORS middleware
- [ ] Create health check endpoint
- [ ] Define Pydantic models

## Acceptance Criteria
- Server starts with uvicorn
- /health returns {status: ok}
- /docs shows Swagger UI"
```

**Closing an Issue:**
```bash
gh issue close 5 --comment "Completed in commit abc123"
```

**Listing Issues:**
```bash
gh issue list --label "phase:mvp"
gh issue list --state open
```

---

## Git Workflow

### Branch Strategy

For this project, we work directly on `main` branch (solo developer, rapid iteration). When the project matures, we may switch to feature branches.

### Commit Message Format

```
[Story X.Y] Brief description

- Detail 1
- Detail 2

Closes #N (if applicable)
```

**Examples:**
```
[Story 3.1] Add FastAPI backend skeleton

- main.py with CORS and health endpoint
- Pydantic models for request/response
- Config with pydantic-settings

[Story 2.1] Implement console log capture

- Intercept console.log/warn/error
- Store entries with timestamps
- Add window.onerror handler

Closes #7
```

### Commit Workflow

1. Before starting work, check current issue status
2. Make changes in logical chunks
3. Test locally before committing
4. Commit with proper message format
5. Push to main
6. Update issue status (close or comment)

```bash
# Check status
gh issue view 5

# Work on code...

# Commit and push
git add .
git commit -m "[Story 3.1] Add FastAPI backend skeleton"
git push

# Close issue
gh issue close 5 --comment "✅ Completed"
```

---

## Development Commands

### Backend

```bash
cd backend

# Setup (first time)
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest

# Check types
mypy app/

# Format code
black app/
isort app/
```

### Bookmarklet

```bash
cd bookmarklet

# No build step needed for development
# Just edit recorder.js and test in browser console

# To create minified bookmarklet (future)
node build.js
```

### GitHub CLI

```bash
# Issues
gh issue list
gh issue view 5
gh issue create --title "..." --label "..." --body "..."
gh issue close 5 --comment "Done"
gh issue edit 5 --add-label "backend"

# Check repo status
gh repo view
gh pr list
```

---

## Task Execution Protocol

When assigned a task, follow this workflow:

### Step 0: Understand Context
1. Read the issue description and acceptance criteria
2. Check parent Epic for broader context
3. Review related code files
4. Identify dependencies on other stories

### Step 1: Plan
1. Break down into concrete steps
2. Identify files to create/modify
3. Consider edge cases
4. Estimate complexity

### Step 2: Implement
1. Create/modify files incrementally
2. Follow project code style
3. Add comments for complex logic
4. Keep functions small and focused

### Step 3: Test
1. Run the code locally
2. Test happy path
3. Test error cases
4. Verify acceptance criteria

### Step 4: Commit
1. Stage relevant files only
2. Write proper commit message
3. Push to main

### Step 5: Update Tracking
1. Comment on issue with summary of changes
2. Update checkboxes in Epic
3. Close issue if fully complete
4. Update ROADMAP.md status

---

## Code Style Guidelines

### Python (Backend)

```python
# Use type hints everywhere
def analyze_error(request: AnalyzeRequest) -> AnalyzeResponse:
    pass

# Pydantic models for all data structures
class ConsoleLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

# Async by default for I/O operations
async def call_llm(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
    return response.json()

# Config via environment variables
from app.config import settings
api_key = settings.gemini_api_key

# Meaningful variable names, no abbreviations
# Good: console_logs, network_errors
# Bad: cl, ne, data
```

### JavaScript (Bookmarklet)

```javascript
// IIFE to avoid global pollution
(function() {
    'use strict';
    
    // All state in one object
    const state = {
        isRecording: false,
        logs: [],
        errors: []
    };
    
    // Clear function names
    function startRecording() { }
    function stopRecording() { }
    function captureConsole() { }
    
    // No external dependencies (must work standalone)
    // No ES6 modules (bookmarklet limitation)
    // Minify-friendly code
})();
```

---

## API Contract

### POST /analyze

**Request:**
```json
{
    "url": "https://example.com/page",
    "user_agent": "Mozilla/5.0...",
    "console_logs": [
        {
            "timestamp": "2025-01-15T10:30:00Z",
            "level": "error",
            "message": "Uncaught TypeError: Cannot read property 'x' of undefined",
            "stack": "at foo (app.js:42)\nat bar (app.js:15)"
        }
    ],
    "network_errors": [
        {
            "timestamp": "2025-01-15T10:30:01Z",
            "method": "POST",
            "url": "https://api.example.com/data",
            "status": 500,
            "status_text": "Internal Server Error"
        }
    ],
    "js_exceptions": [],
    "screenshot": "data:image/png;base64,...",
    "recording_duration_ms": 5000
}
```

**Response:**
```json
{
    "summary": "TypeError due to accessing property of undefined object",
    "probable_cause": "Variable 'user' is null when accessing user.profile.name",
    "suggested_fix": "Add null check: if (user?.profile?.name)",
    "severity": "high",
    "raw_events_count": 5,
    "details": "The error originated in app.js line 42..."
}
```

### GET /health

**Response:**
```json
{
    "status": "ok",
    "version": "0.1.0"
}
```

---

## LLM Provider Interface

All LLM providers must implement this interface:

```python
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze(self, context: str) -> str:
        """Send context to LLM and return analysis."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and accessible."""
        pass
```

**Supported Providers:**
- `GeminiProvider` — Google Gemini 1.5 Flash (primary, 15 RPM free)
- `GroqProvider` — Llama 3.1 70B via Groq (backup, very fast)

---

## Deployment Notes

### Backend (Railway/Vercel)

Environment variables required:
- `LLM_PROVIDER` — "gemini" or "groq"
- `GEMINI_API_KEY` — API key from Google AI Studio
- `GROQ_API_KEY` — API key from Groq Console

### Landing (GitHub Pages)

- Lives in `/landing` directory
- Auto-deployed via GitHub Actions (future)
- Contains bookmarklet installation instructions

---

## Current Status

Check `ROADMAP.md` for up-to-date progress. Key milestones:

- [x] Story 1.1: Repository initialization
- [ ] Story 3.1: Basic FastAPI server ← **CURRENT**
- [ ] Story 4.1: LLM provider abstraction
- [ ] Story 2.1: Basic recorder

---

## Quick Reference

| Action | Command |
|--------|---------|
| Run backend | `cd backend && uvicorn app.main:app --reload` |
| Create issue | `gh issue create --title "..." --label "..." --body "..."` |
| Close issue | `gh issue close N --comment "Done"` |
| Commit | `git commit -m "[Story X.Y] Description"` |
| Push | `git push` |
| Check issues | `gh issue list --state open` |

---

## Notes for Agent

1. **Always read the relevant issue before starting work** — understand context and acceptance criteria
2. **Keep changes focused** — one story = one logical unit of work
3. **Test before committing** — ensure code actually works
4. **Update tracking** — close issues, update ROADMAP checkboxes
5. **Ask for clarification** — if requirements are unclear, ask rather than assume
6. **No over-engineering** — simplest solution that works, refactor later if needed
7. **Document decisions** — add comments explaining "why", not just "what"

When in doubt, refer to this document or ask the project owner.