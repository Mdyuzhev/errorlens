"""LLM-powered comment generation for test code."""

import json
import logging
from urllib.parse import urlparse

from app.config import settings
from app.models_pydantic import RecordedHttpExchange

logger = logging.getLogger(__name__)


def _get_llm_provider():
    """Get LLM provider if configured, None otherwise."""
    try:
        from app.providers.gemini import GeminiProvider
        from app.providers.groq import GroqProvider

        if settings.llm_provider == "groq" and settings.groq_api_key:
            return GroqProvider()
        if settings.gemini_api_key:
            return GeminiProvider()
        if settings.groq_api_key:
            return GroqProvider()
    except Exception as e:
        logger.warning(f"Could not initialize LLM provider: {e}")
    return None


async def generate_llm_comments(recorded_requests: list[RecordedHttpExchange]) -> dict[int, str]:
    """Ask LLM to generate intelligent comments for each request.

    Returns dict mapping request index (1-based) to comment string.
    """
    provider = _get_llm_provider()
    if not provider:
        logger.info("No LLM provider configured, skipping intelligent comments")
        return {}

    # Build context for LLM
    requests_summary = []
    for i, exchange in enumerate(recorded_requests):
        req = exchange.request
        resp = exchange.response
        path = urlparse(req.url).path or "/"

        body_preview = ""
        if req.body:
            try:
                body_dict = json.loads(req.body)
                body_preview = f", body keys: {list(body_dict.keys())[:5]}"
            except (json.JSONDecodeError, TypeError):
                body_preview = ", body: form-data"

        resp_preview = ""
        if resp.body:
            try:
                resp_dict = json.loads(resp.body)
                if isinstance(resp_dict, dict):
                    resp_preview = f", response keys: {list(resp_dict.keys())[:5]}"
            except (json.JSONDecodeError, TypeError):
                pass

        requests_summary.append(
            f"{i+1}. {req.method} {path} -> {resp.status}{body_preview}{resp_preview}"
        )

    prompt = f"""You are a QA engineer writing test comments.

Given this API session flow:
{chr(10).join(requests_summary)}

For EACH request, write a SHORT (1-2 sentences) comment explaining:
- What this request does in business terms
- Why it matters in the test flow

Return JSON object with request numbers as keys:
{{
    "1": "Login request - authenticates user and retrieves JWT token for subsequent API calls",
    "2": "Fetch products list - verifies catalog is accessible after authentication",
    ...
}}

Be concise and professional. Focus on WHAT and WHY, not HOW."""

    try:
        raw_response = await provider.analyze(prompt)

        # Parse response
        text = raw_response.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        comments_dict = json.loads(text)
        # Convert string keys to int
        return {int(k): v for k, v in comments_dict.items()}
    except Exception as e:
        logger.warning(f"Failed to generate LLM comments: {e}")
        return {}
