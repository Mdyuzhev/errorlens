"""Error analysis service with LLM integration."""

import json
import logging

from app.config import settings
from app.models_pydantic import AnalyzeRequest, AnalyzeResponse
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)

# Adaptive prompts based on model size (inspired by Sharmanka)
SYSTEM_PROMPT_SMALL = """Analyze browser errors. Return ONLY valid JSON.

CRITICAL RULES:
1. Output ONLY JSON - no text before/after
2. NO markdown (no ```json or ```)
3. ALL fields required

JSON format:
{"summary":"main problem","probable_cause":"technical reason","suggested_fix":"specific steps","severity":"low|medium|high|critical","details":"extra info"}

SEVERITY GUIDE:
- critical: app crash, data loss, security
- high: main feature broken, 500 errors
- medium: partial failure, 4xx errors
- low: warnings, minor issues

ERROR TYPE PATTERNS:
- TypeError/ReferenceError: null check, optional chaining
- NetworkError 5xx: server issue, check logs
- NetworkError 4xx: client issue, check request
- CORS: backend config issue
- Memory/Stack: infinite loop or leak"""

SYSTEM_PROMPT_MEDIUM = """You are a QA engineer. Analyze browser errors and provide actionable recommendations.

Return ONLY valid JSON with this exact structure:
{
    "summary": "one sentence describing the main problem",
    "probable_cause": "technical root cause",
    "suggested_fix": "specific fix steps",
    "severity": "low|medium|high|critical",
    "details": "additional analysis"
}

RULES:
- NO markdown code blocks (no ```)
- NO text before or after JSON
- ALL 5 fields are required
- Be specific, avoid generic phrases

SEVERITY LEVELS:
- critical: app crash, security issue, data corruption
- high: core feature broken, 500 server errors, auth failures
- medium: non-critical feature issue, 400-499 client errors
- low: warnings, deprecations, minor UI glitches

COMMON PATTERNS:
- TypeError "cannot read property of undefined": missing null check, use optional chaining (?.)
- ReferenceError: variable not defined in scope
- RangeError "Maximum call stack": infinite recursion, check loop conditions
- NetworkError 500: server-side bug, check backend logs
- NetworkError 503: service unavailable, check server health
- NetworkError 429: rate limiting, implement retry with backoff
- CORS error: backend missing Access-Control headers
- WebSocket error: connection lost, implement reconnection logic"""

SYSTEM_PROMPT_LARGE = """You are an expert QA engineer specializing in frontend error analysis.

Analyze the provided browser errors (console logs, JS exceptions, network errors) and return a structured analysis.

OUTPUT FORMAT - Return ONLY this JSON structure, no additional text:
{
    "summary": "Brief description of the main problem (1-2 sentences)",
    "probable_cause": "Technical root cause with specific details",
    "suggested_fix": "Concrete actionable steps to fix the issue",
    "severity": "low|medium|high|critical",
    "details": "In-depth analysis including affected components and potential impact"
}

CRITICAL OUTPUT RULES:
1. First character MUST be '{' - no text before JSON
2. Last character MUST be '}' - no text after JSON
3. NO markdown code blocks (``` or ```json)
4. All 5 fields are REQUIRED
5. Use double quotes for JSON strings
6. Escape special characters in strings

SEVERITY CLASSIFICATION:
- critical: Application crash, security vulnerability, data loss/corruption, complete feature failure
- high: Core functionality broken, 500 server errors, authentication failures, significant UX degradation
- medium: Secondary feature issues, 4xx client errors, recoverable errors with retry
- low: Console warnings, deprecation notices, minor visual glitches, performance hints

ERROR ANALYSIS PATTERNS:

JavaScript Errors:
- TypeError "Cannot read property X of null/undefined": Object not initialized, add null check or optional chaining
- ReferenceError: Variable out of scope or typo in variable name
- RangeError "Maximum call stack size exceeded": Infinite recursion, review recursive function exit conditions
- SyntaxError: Code parsing failed, check for typos or missing brackets

Network Errors:
- 500 Internal Server Error: Backend exception, check server logs for stack trace
- 502 Bad Gateway: Upstream server issue, check proxy/load balancer
- 503 Service Unavailable: Server overloaded or maintenance, implement retry logic
- 504 Gateway Timeout: Backend too slow, optimize query or increase timeout
- 429 Too Many Requests: Rate limited, implement exponential backoff
- 401 Unauthorized: Token expired or invalid, refresh auth token
- 403 Forbidden: Permission denied, check user roles
- 404 Not Found: Wrong endpoint or deleted resource
- CORS errors: Backend needs Access-Control-Allow-Origin header

Browser-Specific:
- WebSocket errors: Connection dropped, implement reconnection with backoff
- IndexedDB errors: Storage quota exceeded or transaction aborted
- Memory warnings: Potential memory leak, check for unremoved listeners

EXAMPLES:

Input: TypeError: Cannot read property 'map' of undefined at Dashboard.render
Output:
{"summary":"Dashboard component crashes due to undefined data array","probable_cause":"The data prop passed to Dashboard is undefined when render() is called, likely because async data hasn't loaded yet","suggested_fix":"Add loading state check: if (!data) return <Loading />; or use optional chaining: data?.map()","severity":"high","details":"Error occurs in Dashboard.render(), indicating the component receives undefined instead of an array. This typically happens when: 1) API call hasn't completed, 2) API returned unexpected format, 3) Parent component passes wrong prop"}

Input: GET /api/cart 503 Service Unavailable (3 times)
Output:
{"summary":"Cart service unavailable causing checkout failure","probable_cause":"Backend cart service is down or overloaded, all 3 retry attempts failed with 503","suggested_fix":"1) Check backend service health and logs, 2) Verify database connections, 3) Scale service if load-related, 4) Add circuit breaker pattern to prevent cascade failures","severity":"critical","details":"Multiple 503 errors indicate persistent backend issue, not transient. Users cannot access cart - direct revenue impact. Immediate investigation required."}"""


def _get_system_prompt(model_size: str = "large") -> str:
    """Get appropriate system prompt based on model size."""
    prompts = {
        "small": SYSTEM_PROMPT_SMALL,  # For 3b models
        "medium": SYSTEM_PROMPT_MEDIUM,  # For 7b models
        "large": SYSTEM_PROMPT_LARGE,  # For cloud/70b+ models
    }
    return prompts.get(model_size, SYSTEM_PROMPT_LARGE)


def _detect_model_size(provider_name: str) -> str:
    """Detect model size from provider name."""
    if "ollama" in provider_name.lower():
        if "3b" in provider_name:
            return "small"
        elif "7b" in provider_name:
            return "medium"
        return "medium"  # Default ollama to medium
    # Cloud providers (groq, gemini) get large prompts
    return "large"


def _get_provider() -> LLMProvider:
    """Get configured LLM provider with fallback."""
    # Ollama (local) - no API key needed
    if settings.llm_provider == "ollama" and settings.ollama_host:
        return OllamaProvider()
    # Groq (cloud)
    if settings.llm_provider == "groq" and settings.groq_api_key:
        return GroqProvider()
    # Gemini (cloud)
    if settings.gemini_api_key:
        return GeminiProvider()
    if settings.groq_api_key:
        return GroqProvider()
    # Fallback to Ollama if available
    if settings.ollama_host:
        return OllamaProvider()
    raise ValueError("No LLM configured. Set GEMINI_API_KEY, GROQ_API_KEY, or OLLAMA_HOST.")


def _format_context(request: AnalyzeRequest, model_size: str = "large") -> str:
    """Format request data into LLM context."""
    system_prompt = _get_system_prompt(model_size)

    parts = [
        system_prompt,
        "",
        "ANALYZE THESE BROWSER ERRORS:",
        "",
        f"URL: {request.url}",
        f"User Agent: {request.user_agent}",
        f"Recording duration: {request.recording_duration_ms}ms",
        "",
    ]

    if request.console_logs:
        parts.append("=== CONSOLE LOGS ===")
        for log in request.console_logs[:50]:  # Limit to prevent token overflow
            parts.append(f"[{log.timestamp}] [{log.level.upper()}] {log.message}")
            if log.stack:
                parts.append(f"  Stack: {log.stack[:500]}")
        parts.append("")

    if request.js_exceptions:
        parts.append("=== JS EXCEPTIONS ===")
        for exc in request.js_exceptions[:20]:
            parts.append(f"[{exc.timestamp}] {exc.message}")
            if exc.source:
                parts.append(f"  File: {exc.source}:{exc.lineno}:{exc.colno}")
            if exc.stack:
                parts.append(f"  Stack: {exc.stack[:500]}")
        parts.append("")

    if request.network_errors:
        parts.append("=== NETWORK ERRORS ===")
        for err in request.network_errors[:30]:
            parts.append(
                f"[{err.timestamp}] {err.method} {err.url} -> {err.status} {err.status_text or ''}"
            )
        parts.append("")

    return "\n".join(parts)


def _parse_llm_response(raw_response: str) -> dict:
    """Parse LLM response JSON, handling common issues."""
    # Try to extract JSON from response (LLM might add extra text)
    text = raw_response.strip()

    # Handle markdown code blocks
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: return raw response as details
        return {
            "summary": "Анализ завершён",
            "probable_cause": "Смотри подробности ниже",
            "suggested_fix": "Изучи детальный анализ",
            "severity": "medium",
            "details": raw_response,
        }


async def analyze_errors(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze error data using LLM."""
    provider = _get_provider()
    logger.info(f"Using LLM provider: {provider.name}")

    # Detect model size for adaptive prompts
    model_size = _detect_model_size(provider.name)
    logger.debug(f"Using {model_size} prompt for {provider.name}")

    context = _format_context(request, model_size)
    raw_response = await provider.analyze(context)

    parsed = _parse_llm_response(raw_response)

    # Ensure details is a string
    details = parsed.get("details", raw_response)
    if isinstance(details, dict):
        details = json.dumps(details, indent=2)

    total_events = (
        len(request.console_logs) + len(request.js_exceptions) + len(request.network_errors)
    )

    return AnalyzeResponse(
        summary=parsed.get("summary", "Анализ завершён"),
        probable_cause=parsed.get("probable_cause", "Неизвестно"),
        suggested_fix=parsed.get("suggested_fix", "Требуется дополнительное исследование"),
        severity=parsed.get("severity", "medium"),
        raw_events_count=total_events,
        details=details,
    )
