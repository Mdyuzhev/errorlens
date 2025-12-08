#!/usr/bin/env python3
"""
LLM Provider Benchmark for ErrorLens.

Compares Groq, Gemini, and Ollama on three test cases:
- Simple: single console error
- Medium: multiple errors + network failure
- Complex: JS exceptions + network errors + console spam
"""

import asyncio
import json
import time
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.providers.groq import GroqProvider
from app.providers.gemini import GeminiProvider
from app.providers.ollama import OllamaProvider

# =============================================================================
# ADAPTIVE PROMPTS (from analyzer.py)
# =============================================================================

PROMPT_SMALL = """Analyze browser errors. Return ONLY valid JSON.

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

PROMPT_MEDIUM = """You are a QA engineer. Analyze browser errors and provide actionable recommendations.

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

PROMPT_LARGE = """You are an expert QA engineer specializing in frontend error analysis.

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

Network Errors:
- 500 Internal Server Error: Backend exception, check server logs for stack trace
- 503 Service Unavailable: Server overloaded or maintenance, implement retry logic
- 429 Too Many Requests: Rate limited, implement exponential backoff
- CORS errors: Backend needs Access-Control-Allow-Origin header

EXAMPLES:

Input: TypeError: Cannot read property 'map' of undefined at Dashboard.render
Output:
{"summary":"Dashboard component crashes due to undefined data array","probable_cause":"The data prop passed to Dashboard is undefined when render() is called","suggested_fix":"Add loading state check: if (!data) return <Loading />; or use optional chaining: data?.map()","severity":"high","details":"Error occurs in Dashboard.render(), indicating the component receives undefined instead of an array"}

Input: GET /api/cart 503 Service Unavailable (3 times)
Output:
{"summary":"Cart service unavailable causing checkout failure","probable_cause":"Backend cart service is down or overloaded, all 3 retry attempts failed with 503","suggested_fix":"1) Check backend service health and logs, 2) Verify database connections, 3) Scale service if load-related","severity":"critical","details":"Multiple 503 errors indicate persistent backend issue. Users cannot access cart - direct revenue impact."}"""


def get_prompt_for_model(model_name: str) -> str:
    """Get appropriate prompt based on model size."""
    model_lower = model_name.lower()
    if "3b" in model_lower:
        return PROMPT_SMALL
    elif "7b" in model_lower:
        return PROMPT_MEDIUM
    else:
        return PROMPT_LARGE  # Cloud models, 70b+

# =============================================================================
# TEST CASES
# =============================================================================

TEST_SIMPLE = """
Проанализируй следующие ошибки браузера:

URL страницы: https://example.com/dashboard
User Agent: Mozilla/5.0 Chrome/120
Длительность записи: 5000мс

=== Логи консоли ===
[2024-01-15T10:30:00Z] [ERROR] Uncaught TypeError: Cannot read property 'name' of undefined
  Стек: at UserProfile.render (app.js:142:15)
"""

TEST_MEDIUM = """
Проанализируй следующие ошибки браузера:

URL страницы: https://shop.example.com/checkout
User Agent: Mozilla/5.0 Chrome/120
Длительность записи: 15000мс

=== Логи консоли ===
[2024-01-15T10:30:00Z] [ERROR] Failed to fetch user cart
[2024-01-15T10:30:01Z] [WARN] Retrying API call (attempt 2/3)
[2024-01-15T10:30:02Z] [ERROR] All retry attempts failed
[2024-01-15T10:30:03Z] [ERROR] Uncaught Error: Cart data unavailable

=== Сетевые ошибки ===
[2024-01-15T10:30:00Z] GET /api/cart -> 503 Service Unavailable
[2024-01-15T10:30:01Z] GET /api/cart -> 503 Service Unavailable
[2024-01-15T10:30:02Z] GET /api/cart -> 503 Service Unavailable
"""

TEST_COMPLEX = """
Проанализируй следующие ошибки браузера:

URL страницы: https://app.example.com/analytics/reports
User Agent: Mozilla/5.0 Chrome/120
Длительность записи: 45000мс

=== Логи консоли ===
[2024-01-15T10:30:00Z] [LOG] App initialized
[2024-01-15T10:30:01Z] [WARN] Performance warning: render took 850ms
[2024-01-15T10:30:02Z] [ERROR] WebSocket connection failed
[2024-01-15T10:30:03Z] [ERROR] Failed to load report data
[2024-01-15T10:30:04Z] [WARN] Memory usage high: 1.2GB
[2024-01-15T10:30:05Z] [ERROR] ChartJS: Invalid data format
[2024-01-15T10:30:06Z] [ERROR] Uncaught RangeError: Maximum call stack size exceeded
  Стек: at processData (analytics.js:542) at processData (analytics.js:545) at processData...
[2024-01-15T10:30:07Z] [ERROR] React: Cannot update unmounted component
[2024-01-15T10:30:08Z] [WARN] IndexedDB transaction aborted

=== JavaScript исключения ===
[2024-01-15T10:30:06Z] RangeError: Maximum call stack size exceeded
  Файл: analytics.js:542:18
  Стек: at processData (analytics.js:542:18) at processData (analytics.js:545:22)...

[2024-01-15T10:30:09Z] TypeError: Cannot read properties of null (reading 'chartInstance')
  Файл: chart-component.js:89:12
  Стек: at ChartComponent.updateChart (chart-component.js:89:12)

=== Сетевые ошибки ===
[2024-01-15T10:30:02Z] GET wss://api.example.com/ws -> 0 WebSocket Error
[2024-01-15T10:30:03Z] GET /api/reports/weekly -> 500 Internal Server Error
[2024-01-15T10:30:04Z] POST /api/analytics/track -> 429 Too Many Requests
[2024-01-15T10:30:10Z] GET /api/export/pdf -> 504 Gateway Timeout
"""

TESTS = {
    "simple": {"name": "Simple (1 error)", "context": TEST_SIMPLE},
    "medium": {"name": "Medium (retry+503)", "context": TEST_MEDIUM},
    "complex": {"name": "Complex (multi)", "context": TEST_COMPLEX},
}

# =============================================================================
# BENCHMARK FUNCTIONS
# =============================================================================

def parse_response(response: str) -> dict:
    """Try to parse JSON from LLM response."""
    text = response.strip()

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
    except:
        return None


def score_response(response: str) -> dict:
    """Score response quality."""
    parsed = parse_response(response)

    return {
        "valid_json": parsed is not None,
        "has_severity": parsed and "severity" in parsed,
        "has_fix": parsed and len(parsed.get("suggested_fix", "")) > 10,
        "has_cause": parsed and len(parsed.get("probable_cause", "")) > 10,
        "response_len": len(response),
    }


async def run_single_test(provider, context: str, model_name: str) -> dict:
    """Run single test and measure time/quality."""
    system_prompt = get_prompt_for_model(model_name)
    full_context = system_prompt + "\n\nANALYZE THESE BROWSER ERRORS:\n" + context

    start = time.perf_counter()
    try:
        response = await provider.analyze(full_context)
        elapsed = time.perf_counter() - start
        scores = score_response(response)

        return {
            "success": True,
            "time_sec": round(elapsed, 2),
            **scores,
            "preview": response[:300] + "..." if len(response) > 300 else response,
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "success": False,
            "time_sec": round(elapsed, 2),
            "error": str(e)[:100],
        }


async def benchmark_provider(name: str, provider, tests: dict, model_name: str) -> dict:
    """Run all tests for a provider."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  Prompt: {get_prompt_for_model(model_name)[:50]}...")
    print(f"{'='*60}")

    results = {}
    for test_key, test_data in tests.items():
        print(f"\n  [{test_data['name']}] ", end="", flush=True)
        result = await run_single_test(provider, test_data["context"], model_name)
        results[test_key] = result

        if result["success"]:
            status = "[OK]" if result["valid_json"] else "[~]"
            print(f"{status} {result['time_sec']}s | JSON:{result['valid_json']} fix:{result['has_fix']} cause:{result['has_cause']}")
        else:
            print(f"[FAIL] {result.get('error', 'Unknown error')}")

    return results


async def main():
    print("\n" + "="*60)
    print("  ErrorLens LLM Benchmark (3 difficulty levels)")
    print("="*60)

    print(f"\nTests:")
    print(f"  1. Simple  - single TypeError")
    print(f"  2. Medium  - API retry failure (503)")
    print(f"  3. Complex - multiple errors, stack overflow, network issues")

    print(f"\nProviders:")
    print(f"  - Groq (llama-3.3-70b):   {'[OK]' if settings.groq_api_key else '[NO KEY]'}")
    print(f"  - Gemini (1.5-flash):     {'[OK]' if settings.gemini_api_key else '[NO KEY]'}")
    print(f"  - Ollama ({settings.ollama_model}): {settings.ollama_host}")

    all_results = {}

    # Groq
    if settings.groq_api_key:
        try:
            all_results["Groq"] = await benchmark_provider(
                "Groq (Llama 3.3 70B)", GroqProvider(), TESTS, "llama-3.3-70b"
            )
        except Exception as e:
            print(f"\n[FAIL] Groq: {e}")
            all_results["Groq"] = {"error": str(e)}
    else:
        print("\n[SKIP] Groq (no API key)")

    # Gemini
    if settings.gemini_api_key:
        try:
            all_results["Gemini"] = await benchmark_provider(
                "Gemini (1.5 Flash)", GeminiProvider(), TESTS, "gemini-1.5-flash"
            )
        except Exception as e:
            print(f"\n[FAIL] Gemini: {e}")
            all_results["Gemini"] = {"error": str(e)}
    else:
        print("\n[SKIP] Gemini (no API key)")

    # Ollama
    try:
        import httpx
        resp = httpx.get(f"{settings.ollama_host}/api/tags", timeout=5)
        if resp.status_code == 200:
            all_results["Ollama"] = await benchmark_provider(
                f"Ollama ({settings.ollama_model})", OllamaProvider(), TESTS, settings.ollama_model
            )
        else:
            print(f"\n[SKIP] Ollama (server not responding)")
    except Exception as e:
        print(f"\n[SKIP] Ollama: {e}")

    # ==========================================================================
    # SUMMARY TABLE
    # ==========================================================================
    print("\n" + "="*70)
    print("  SUMMARY TABLE")
    print("="*70)
    print(f"\n{'Provider':<15} {'Simple':<15} {'Medium':<15} {'Complex':<15} {'Avg':<10}")
    print("-"*70)

    for provider_name, results in all_results.items():
        if "error" in results:
            print(f"{provider_name:<15} {'ERROR':<15} {'-':<15} {'-':<15} {'-':<10}")
            continue

        times = []
        json_ok = []
        row = [provider_name]

        for test_key in ["simple", "medium", "complex"]:
            r = results.get(test_key, {})
            if r.get("success"):
                t = r["time_sec"]
                times.append(t)
                json_ok.append(r.get("valid_json", False))
                mark = "V" if r.get("valid_json") else "~"
                row.append(f"{t}s {mark}")
            else:
                row.append("FAIL")

        avg = f"{sum(times)/len(times):.2f}s" if times else "-"
        row.append(avg)
        print(f"{row[0]:<15} {row[1]:<15} {row[2]:<15} {row[3]:<15} {row[4]:<10}")

    print("-"*70)
    print("V = valid JSON, ~ = text response (no JSON)")

    # ==========================================================================
    # QUALITY COMPARISON
    # ==========================================================================
    print("\n" + "="*70)
    print("  QUALITY METRICS")
    print("="*70)
    print(f"\n{'Provider':<15} {'JSON OK':<10} {'Has Fix':<10} {'Has Cause':<12} {'Avg Len':<10}")
    print("-"*70)

    for provider_name, results in all_results.items():
        if "error" in results:
            continue

        json_count = 0
        fix_count = 0
        cause_count = 0
        lengths = []

        for test_key in ["simple", "medium", "complex"]:
            r = results.get(test_key, {})
            if r.get("success"):
                if r.get("valid_json"):
                    json_count += 1
                if r.get("has_fix"):
                    fix_count += 1
                if r.get("has_cause"):
                    cause_count += 1
                lengths.append(r.get("response_len", 0))

        avg_len = int(sum(lengths) / len(lengths)) if lengths else 0
        print(f"{provider_name:<15} {json_count}/3{'':<6} {fix_count}/3{'':<6} {cause_count}/3{'':<8} {avg_len:<10}")

    # ==========================================================================
    # SAMPLE RESPONSES
    # ==========================================================================
    print("\n" + "="*70)
    print("  SAMPLE RESPONSES (Complex test, first 400 chars)")
    print("="*70)

    for provider_name, results in all_results.items():
        if "error" in results:
            continue
        r = results.get("complex", {})
        if r.get("success") and r.get("preview"):
            print(f"\n--- {provider_name} ---")
            print(r["preview"][:400])

    print("\n" + "="*70)
    print("  BENCHMARK COMPLETE")
    print("="*70 + "\n")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())
