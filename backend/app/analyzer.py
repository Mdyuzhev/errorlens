"""Error analysis service with LLM integration."""

import json
import logging

from app.config import settings
from app.models import AnalyzeRequest, AnalyzeResponse
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """CRITICAL: You MUST respond in Russian language only. All text values in JSON must be in Russian.

You are an expert QA engineer and frontend debugger. Analyze the following browser error data.

The data includes:
- Console logs (errors, warnings)
- Network failures (4xx/5xx responses)
- JavaScript exceptions

Respond in JSON format with these fields (ALL VALUES MUST BE IN RUSSIAN):
{
  "summary": "Краткое описание проблемы (на русском)",
  "probable_cause": "Вероятная причина ошибки (на русском)",
  "suggested_fix": "Рекомендация по исправлению (на русском)",
  "severity": "low|medium|high|critical",
  "details": "Подробный технический анализ (на русском)"
}

Remember: ALL text content MUST be in Russian language!"""


def _get_provider() -> LLMProvider:
    """Get configured LLM provider with fallback."""
    if settings.llm_provider == "groq" and settings.groq_api_key:
        return GroqProvider()
    if settings.gemini_api_key:
        return GeminiProvider()
    if settings.groq_api_key:
        return GroqProvider()
    raise ValueError("No LLM API key configured. Set GEMINI_API_KEY or GROQ_API_KEY.")


def _format_context(request: AnalyzeRequest) -> str:
    """Format request data into LLM context."""
    parts = [
        SYSTEM_PROMPT,
        "",
        f"Page URL: {request.url}",
        f"User Agent: {request.user_agent}",
        f"Recording Duration: {request.recording_duration_ms}ms",
        "",
    ]

    if request.console_logs:
        parts.append("=== Console Logs ===")
        for log in request.console_logs[:50]:  # Limit to prevent token overflow
            parts.append(f"[{log.timestamp}] [{log.level.upper()}] {log.message}")
            if log.stack:
                parts.append(f"  Stack: {log.stack[:500]}")
        parts.append("")

    if request.js_exceptions:
        parts.append("=== JavaScript Exceptions ===")
        for exc in request.js_exceptions[:20]:
            parts.append(f"[{exc.timestamp}] {exc.message}")
            if exc.source:
                parts.append(f"  Source: {exc.source}:{exc.lineno}:{exc.colno}")
            if exc.stack:
                parts.append(f"  Stack: {exc.stack[:500]}")
        parts.append("")

    if request.network_errors:
        parts.append("=== Network Errors ===")
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
            "summary": "Analysis completed",
            "probable_cause": "See details for full analysis",
            "suggested_fix": "Review the detailed analysis below",
            "severity": "medium",
            "details": raw_response,
        }


async def analyze_errors(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze error data using LLM."""
    provider = _get_provider()
    logger.info(f"Using LLM provider: {provider.name}")

    context = _format_context(request)
    raw_response = await provider.analyze(context)

    parsed = _parse_llm_response(raw_response)

    # Ensure details is a string
    details = parsed.get("details", raw_response)
    if isinstance(details, dict):
        details = json.dumps(details, indent=2)

    total_events = (
        len(request.console_logs)
        + len(request.js_exceptions)
        + len(request.network_errors)
    )

    return AnalyzeResponse(
        summary=parsed.get("summary", "Analysis completed"),
        probable_cause=parsed.get("probable_cause", "Unknown"),
        suggested_fix=parsed.get("suggested_fix", "Further investigation needed"),
        severity=parsed.get("severity", "medium"),
        raw_events_count=total_events,
        details=details,
    )
