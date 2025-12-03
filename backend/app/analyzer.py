"""Error analysis service with LLM integration."""

import json
import logging

from app.config import settings
from app.models import AnalyzeRequest, AnalyzeResponse
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — опытный QA-инженер. Анализируй ошибки браузера и давай практичные рекомендации.

Входные данные: console-логи, сетевые ошибки, JS-исключения с веб-страницы.

Твоя задача:
1. Определить главную проблему
2. Найти вероятную причину
3. Предложить конкретное решение
4. Оценить критичность (low/medium/high/critical)

Отвечай строго в JSON-формате:
{
    "summary": "краткое описание главной проблемы",
    "probable_cause": "техническая причина ошибки",
    "suggested_fix": "конкретные шаги для исправления",
    "severity": "low|medium|high|critical",
    "details": "дополнительный анализ если нужен"
}

Примеры хороших ответов:

Для TypeError:
{
    "summary": "Ошибка доступа к свойству несуществующего объекта",
    "probable_cause": "Переменная user равна null или undefined при обращении к user.profile",
    "suggested_fix": "Добавить проверку: if (user?.profile) { ... } или использовать optional chaining",
    "severity": "medium",
    "details": "Ошибка в файле app.js:42, вызвана отсутствием данных пользователя"
}

Для сетевой ошибки 500:
{
    "summary": "Сервер вернул внутреннюю ошибку",
    "probable_cause": "Сбой на бэкенде при обработке запроса к /api/users",
    "suggested_fix": "Проверить логи сервера, убедиться что БД доступна, проверить валидность входных данных",
    "severity": "high",
    "details": "POST запрос к /api/users вернул 500 Internal Server Error"
}

Будь конкретным и практичным. Избегай общих фраз."""


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
        "Проанализируй следующие ошибки браузера:",
        "",
        f"URL страницы: {request.url}",
        f"User Agent: {request.user_agent}",
        f"Длительность записи: {request.recording_duration_ms}мс",
        "",
    ]

    if request.console_logs:
        parts.append("=== Логи консоли ===")
        for log in request.console_logs[:50]:  # Limit to prevent token overflow
            parts.append(f"[{log.timestamp}] [{log.level.upper()}] {log.message}")
            if log.stack:
                parts.append(f"  Стек: {log.stack[:500]}")
        parts.append("")

    if request.js_exceptions:
        parts.append("=== JavaScript исключения ===")
        for exc in request.js_exceptions[:20]:
            parts.append(f"[{exc.timestamp}] {exc.message}")
            if exc.source:
                parts.append(f"  Файл: {exc.source}:{exc.lineno}:{exc.colno}")
            if exc.stack:
                parts.append(f"  Стек: {exc.stack[:500]}")
        parts.append("")

    if request.network_errors:
        parts.append("=== Сетевые ошибки ===")
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
        summary=parsed.get("summary", "Анализ завершён"),
        probable_cause=parsed.get("probable_cause", "Неизвестно"),
        suggested_fix=parsed.get("suggested_fix", "Требуется дополнительное исследование"),
        severity=parsed.get("severity", "medium"),
        raw_events_count=total_events,
        details=details,
    )
