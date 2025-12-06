"""Generate smart bug tickets from session analysis with auto-steps."""

from datetime import datetime
from urllib.parse import urlparse


def generate_ticket(
    analysis: dict,
    url: str,
    user_agent: str,
    additional_info: str = "",
    format: str = "jira",
) -> dict:
    """Generate formatted bug ticket from analysis (backward compatible)."""
    return generate_smart_ticket(
        analysis=analysis,
        url=url,
        user_agent=user_agent,
        additional_info=additional_info,
        format=format,
    )


def generate_smart_ticket(
    analysis: dict,
    url: str,
    user_agent: str,
    recorded_requests: list[dict] = None,
    console_logs: list[dict] = None,
    js_exceptions: list[dict] = None,
    additional_info: str = "",
    format: str = "jira",
) -> dict:
    """Generate smart ticket with auto-steps from recorded session."""

    severity_map = {
        "critical": {"jira": "Blocker", "github": "critical", "emoji": "🔴", "color": "#d73a49"},
        "high": {"jira": "Critical", "github": "high", "emoji": "🟠", "color": "#f66a0a"},
        "medium": {"jira": "Major", "github": "medium", "emoji": "🟡", "color": "#dbab09"},
        "low": {"jira": "Minor", "github": "low", "emoji": "🟢", "color": "#28a745"},
    }

    severity = analysis.get("severity", "medium")
    sev = severity_map.get(severity, severity_map["medium"])

    # Generate auto-steps from recorded requests
    auto_steps = _generate_auto_steps(recorded_requests) if recorded_requests else []

    # Generate timeline
    timeline = _generate_timeline(recorded_requests, console_logs, js_exceptions)

    # Find problematic request
    problem_request = _find_problem_request(recorded_requests)

    # Generate request chain table
    request_chain = _generate_request_chain(recorded_requests)

    if format == "jira":
        return _format_jira_smart(
            analysis,
            url,
            user_agent,
            additional_info,
            sev,
            auto_steps,
            timeline,
            problem_request,
            request_chain,
        )
    elif format == "github":
        return _format_github_smart(
            analysis,
            url,
            user_agent,
            additional_info,
            sev,
            auto_steps,
            timeline,
            problem_request,
            request_chain,
        )
    else:
        return _format_markdown_smart(
            analysis,
            url,
            user_agent,
            additional_info,
            sev,
            auto_steps,
            timeline,
            problem_request,
            request_chain,
        )


def _generate_auto_steps(recorded_requests: list[dict]) -> list[str]:
    """Generate steps from recorded HTTP requests."""
    if not recorded_requests:
        return []

    steps = []
    steps.append("Открыть страницу в браузере")

    for _i, req in enumerate(recorded_requests):
        request = req.get("request", req)
        method = request.get("method", "GET")
        url = request.get("url", "")

        path = urlparse(url).path or "/"

        response = req.get("response", {})
        status = response.get("status", 0)

        if status >= 400:
            steps.append(f"⚠️ {method} {path} → **{status} ошибка**")
        else:
            # Simplify common patterns
            path_lower = path.lower()
            if "/login" in path_lower or "/auth" in path_lower:
                steps.append("Авторизоваться в системе")
            elif "/logout" in path_lower:
                steps.append("Выйти из системы")
            elif "/register" in path_lower or "/signup" in path_lower:
                steps.append("Зарегистрироваться")
            elif "/cart" in path_lower:
                steps.append("Открыть корзину")
            elif "/checkout" in path_lower:
                steps.append("Перейти к оформлению заказа")
            elif "/order" in path_lower:
                if method == "POST":
                    steps.append("Создать заказ")
                else:
                    steps.append("Просмотреть заказ")
            elif "/product" in path_lower:
                if method == "POST":
                    steps.append("Добавить товар")
                else:
                    steps.append("Просмотреть товар")
            elif "/api/" in path:
                steps.append(f"Система выполняет {method} запрос на {path[:40]}")
            else:
                if len(steps) < 10:  # Limit steps
                    steps.append(f"{method} {path[:40]} → {status}")

    return steps[:15]  # Max 15 steps


def _generate_timeline(
    recorded_requests: list[dict], console_logs: list[dict], js_exceptions: list[dict]
) -> list[dict]:
    """Generate unified timeline of events."""
    events = []

    # Add requests
    if recorded_requests:
        for req in recorded_requests:
            timestamp = req.get("timestamp", "")
            request = req.get("request", req)
            response = req.get("response", {})
            events.append(
                {
                    "time": timestamp,
                    "type": "request",
                    "method": request.get("method", ""),
                    "url": request.get("url", ""),
                    "status": response.get("status", 0),
                    "is_error": response.get("status", 0) >= 400,
                }
            )

    # Add console errors
    if console_logs:
        for log in console_logs:
            if log.get("level") in ("error", "warn"):
                events.append(
                    {
                        "time": log.get("timestamp", ""),
                        "type": "console",
                        "level": log.get("level"),
                        "message": log.get("message", "")[:100],
                    }
                )

    # Add JS exceptions
    if js_exceptions:
        for exc in js_exceptions:
            events.append(
                {
                    "time": exc.get("timestamp", ""),
                    "type": "exception",
                    "message": exc.get("message", "")[:100],
                }
            )

    # Sort by time
    events.sort(key=lambda x: x.get("time", ""))

    return events


def _find_problem_request(recorded_requests: list[dict]) -> dict | None:
    """Find the request that likely caused the error."""
    if not recorded_requests:
        return None

    # First look for 5xx errors
    for req in recorded_requests:
        response = req.get("response", {})
        if 500 <= response.get("status", 0) < 600:
            return req

    # Then 4xx errors
    for req in recorded_requests:
        response = req.get("response", {})
        if 400 <= response.get("status", 0) < 500:
            return req

    return None


def _generate_request_chain(recorded_requests: list[dict]) -> str:
    """Generate markdown table of request chain."""
    if not recorded_requests:
        return ""

    lines = [
        "| # | Method | Path | Status | Duration |",
        "|---|--------|------|--------|----------|",
    ]

    for i, req in enumerate(recorded_requests[:20]):  # Max 20 rows
        request = req.get("request", req)
        response = req.get("response", {})

        method = request.get("method", "GET")
        url = request.get("url", "")
        path = urlparse(url).path or "/"
        if len(path) > 40:
            path = path[:37] + "..."

        status = response.get("status", 0)
        duration = response.get("duration_ms", 0)

        # Mark errors
        status_str = f"**{status}** ⚠️" if status >= 400 else str(status)

        lines.append(f"| {i+1} | {method} | {path} | {status_str} | {duration}ms |")

    return "\n".join(lines)


def _format_headers(headers: dict) -> str:
    """Format headers as text."""
    if not headers:
        return "(нет заголовков)"
    return "\n".join(f"{k}: {v}" for k, v in list(headers.items())[:10])


def _format_jira_smart(
    analysis,
    url,
    user_agent,
    additional_info,
    sev,
    auto_steps,
    timeline,
    problem_request,
    request_chain,
) -> dict:
    """Format as Jira ticket with smart features."""
    summary = analysis.get("summary", "Ошибка на странице")
    probable_cause = analysis.get("probable_cause", "Требует анализа")
    suggested_fix = analysis.get("suggested_fix", "Требует анализа")

    # Build steps section
    if auto_steps:
        steps_text = "\n".join(f"# {step}" for step in auto_steps)
    else:
        steps_text = "# Открыть страницу\n# Выполнить действия\n# Наблюдать ошибку"

    # Build timeline section
    timeline_text = ""
    if timeline:
        timeline_text = "\nh2. Timeline событий\n||Время||Тип||Описание||\n"
        for event in timeline[-10:]:  # Last 10 events
            time_short = (
                event["time"].split("T")[1][:8]
                if "T" in str(event.get("time", ""))
                else str(event.get("time", ""))[:8]
            )
            if event["type"] == "request":
                status_icon = "❌" if event["is_error"] else "✅"
                url_short = event["url"][-30:] if len(event["url"]) > 30 else event["url"]
                desc = f"{status_icon} {event['method']} ...{url_short} → {event['status']}"
            elif event["type"] == "console":
                desc = f"📋 [{event['level']}] {event['message'][:50]}"
            else:
                desc = f"💥 {event['message'][:50]}"
            timeline_text += f"|{time_short}|{event['type']}|{desc}|\n"

    # Build problem request section
    problem_text = ""
    if problem_request:
        req = problem_request.get("request", problem_request)
        resp = problem_request.get("response", {})
        problem_text = f"""
h2. Проблемный запрос

*Method:* {req.get('method')}
*URL:* {req.get('url')}
*Status:* {resp.get('status')} {resp.get('status_text', '')}

h3. Request Headers
{{code}}
{_format_headers(req.get('headers', {}))}
{{code}}

h3. Response Body (первые 500 символов)
{{code}}
{str(resp.get('body', ''))[:500]}
{{code}}
"""

    # Build request chain section
    chain_text = ""
    if request_chain:
        chain_text = f"\nh2. Цепочка запросов\n{request_chain}"

    description = f"""h2. Описание
{summary}

h2. Шаги воспроизведения
{steps_text}

h2. Ожидаемый результат
Страница работает без ошибок

h2. Фактический результат
{summary}

h2. Анализ

*Вероятная причина:* {probable_cause}

*Рекомендуемое исправление:* {suggested_fix}
{timeline_text}
{problem_text}
{chain_text}

h2. Окружение
* URL: {url}
* User-Agent: {user_agent}
* Дата: {datetime.now().strftime("%Y-%m-%d %H:%M")}

{f"h2. Дополнительная информация{chr(10)}{additional_info}" if additional_info else ""}

----
_Создано с помощью ErrorLens_
"""

    return {
        "title": f"[BUG] {summary[:80]}",
        "description": description,
        "priority": sev["jira"],
        "labels": ["bug", "errorlens"],
        "format": "jira",
    }


def _format_github_smart(
    analysis,
    url,
    user_agent,
    additional_info,
    sev,
    auto_steps,
    timeline,
    problem_request,
    request_chain,
) -> dict:
    """Format as GitHub issue with smart features."""
    summary = analysis.get("summary", "Ошибка на странице")
    probable_cause = analysis.get("probable_cause", "Требует анализа")
    suggested_fix = analysis.get("suggested_fix", "Требует анализа")
    severity = analysis.get("severity", "medium")

    # Build steps
    if auto_steps:
        steps_md = "\n".join(f"{i}. {step}" for i, step in enumerate(auto_steps, 1))
    else:
        steps_md = "1. Открыть страницу\n2. Выполнить действия\n3. Наблюдать ошибку"

    # Build timeline
    timeline_md = ""
    if timeline:
        timeline_md = (
            "\n### Timeline событий\n\n| Время | Тип | Описание |\n|-------|-----|----------|\n"
        )
        for event in timeline[-10:]:
            time_short = (
                event["time"].split("T")[1][:8]
                if "T" in str(event.get("time", ""))
                else str(event.get("time", ""))[:8]
            )
            if event["type"] == "request":
                status_icon = "❌" if event["is_error"] else "✅"
                desc = f"{status_icon} {event['method']} → {event['status']}"
            elif event["type"] == "console":
                desc = f"📋 [{event['level']}] {event['message'][:40]}"
            else:
                desc = f"💥 {event['message'][:40]}"
            timeline_md += f"| {time_short} | {event['type']} | {desc} |\n"

    # Build problem request details
    problem_md = ""
    if problem_request:
        req = problem_request.get("request", problem_request)
        resp = problem_request.get("response", {})
        problem_md = f"""
### Проблемный запрос

- **Method:** {req.get('method')}
- **URL:** `{req.get('url')}`
- **Status:** {resp.get('status')} {resp.get('status_text', '')}

<details>
<summary>Request Headers</summary>

```
{_format_headers(req.get('headers', {}))}
```
</details>

<details>
<summary>Response Body (первые 500 символов)</summary>

```json
{str(resp.get('body', ''))[:500]}
```
</details>
"""

    # Build request chain
    chain_md = ""
    if request_chain:
        chain_md = f"\n### Цепочка запросов\n\n{request_chain}"

    body = f"""## Описание
{summary}

## Шаги воспроизведения
{steps_md}

## Ожидаемый результат
Страница работает без ошибок

## Фактический результат
{summary}

## Анализ

**Вероятная причина:** {probable_cause}

**Рекомендуемое исправление:** {suggested_fix}
{timeline_md}
{problem_md}
{chain_md}

## Окружение
- **URL:** {url}
- **User-Agent:** `{user_agent[:50]}...`
- **Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **Severity:** {sev["emoji"]} {severity}

{f"## Дополнительная информация{chr(10)}{additional_info}" if additional_info else ""}

---
*Создано с помощью [ErrorLens](https://github.com/Mdyuzhev/errorlens)*
"""

    return {
        "title": f"🐛 {summary[:80]}",
        "body": body,
        "labels": ["bug", sev["github"]],
        "format": "github",
    }


def _format_markdown_smart(
    analysis,
    url,
    user_agent,
    additional_info,
    sev,
    auto_steps,
    timeline,
    problem_request,
    request_chain,
) -> dict:
    """Format as plain markdown with smart features."""
    summary = analysis.get("summary", "Ошибка на странице")
    probable_cause = analysis.get("probable_cause", "Требует анализа")
    suggested_fix = analysis.get("suggested_fix", "Требует анализа")
    severity = analysis.get("severity", "medium")

    steps_md = (
        "\n".join(f"{i}. {step}" for i, step in enumerate(auto_steps, 1))
        if auto_steps
        else "1. Открыть страницу"
    )

    # Build request chain
    chain_md = ""
    if request_chain:
        chain_md = f"\n## Цепочка запросов\n{request_chain}"

    content = f"""# 🐛 Баг-репорт

**Severity:** {sev["emoji"]} {severity.upper()}
**URL:** {url}
**Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Описание
{summary}

## Шаги воспроизведения
{steps_md}

## Вероятная причина
{probable_cause}

## Рекомендуемое исправление
{suggested_fix}
{chain_md}

{f"## Дополнительно{chr(10)}{additional_info}" if additional_info else ""}

---
*Создано с помощью ErrorLens*
"""

    return {"title": f"🐛 {summary[:80]}", "content": content, "format": "markdown"}
