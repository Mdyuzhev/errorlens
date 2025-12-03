"""Generate bug tickets from session analysis."""

from datetime import datetime


def generate_ticket(
    analysis: dict,
    url: str,
    user_agent: str,
    additional_info: str = "",
    format: str = "jira",
) -> dict:
    """Generate formatted bug ticket from analysis."""
    severity_map = {
        "critical": {"jira": "Blocker", "github": "critical", "emoji": "🔴"},
        "high": {"jira": "Critical", "github": "high", "emoji": "🟠"},
        "medium": {"jira": "Major", "github": "medium", "emoji": "🟡"},
        "low": {"jira": "Minor", "github": "low", "emoji": "🟢"},
    }

    severity = analysis.get("severity", "medium")
    sev = severity_map.get(severity, severity_map["medium"])

    if format == "jira":
        return _format_jira(analysis, url, user_agent, additional_info, sev)
    elif format == "github":
        return _format_github(analysis, url, user_agent, additional_info, sev)
    else:
        return _format_markdown(analysis, url, user_agent, additional_info, sev)


def _format_jira(analysis, url, user_agent, additional_info, sev) -> dict:
    """Format as Jira ticket."""
    summary = analysis.get("summary", "Ошибка на странице")
    probable_cause = analysis.get("probable_cause", "Не определена")
    suggested_fix = analysis.get("suggested_fix", "Требует анализа")

    description = f"""h2. Описание
{summary}

h2. Шаги воспроизведения
# Открыть страницу: {url}
# Выполнить действия, приводящие к ошибке
# Наблюдать ошибку в консоли браузера

h2. Ожидаемый результат
Страница работает без ошибок

h2. Фактический результат
{summary}

h2. Вероятная причина
{probable_cause}

h2. Рекомендуемое исправление
{suggested_fix}

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


def _format_github(analysis, url, user_agent, additional_info, sev) -> dict:
    """Format as GitHub issue."""
    summary = analysis.get("summary", "Ошибка на странице")
    probable_cause = analysis.get("probable_cause", "Не определена")
    suggested_fix = analysis.get("suggested_fix", "Требует анализа")
    severity = analysis.get("severity", "medium")

    body = f"""## Описание
{summary}

## Шаги воспроизведения
1. Открыть страницу: {url}
2. Выполнить действия, приводящие к ошибке
3. Наблюдать ошибку в консоли браузера

## Ожидаемый результат
Страница работает без ошибок

## Фактический результат
{summary}

## Анализ

**Вероятная причина:** {probable_cause}

**Рекомендуемое исправление:** {suggested_fix}

## Окружение
- **URL:** {url}
- **User-Agent:** {user_agent}
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


def _format_markdown(analysis, url, user_agent, additional_info, sev) -> dict:
    """Format as plain markdown."""
    summary = analysis.get("summary", "Ошибка на странице")
    probable_cause = analysis.get("probable_cause", "Не определена")
    suggested_fix = analysis.get("suggested_fix", "Требует анализа")
    details = analysis.get("details", "")
    severity = analysis.get("severity", "medium")

    content = f"""# 🐛 Баг-репорт

**Severity:** {sev["emoji"]} {severity.upper()}
**URL:** {url}
**Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Описание
{summary}

## Вероятная причина
{probable_cause}

## Рекомендуемое исправление
{suggested_fix}

## Детали
{details}

{f"## Дополнительно{chr(10)}{additional_info}" if additional_info else ""}

---
*Создано с помощью ErrorLens*
"""

    return {
        "title": f"🐛 {summary[:80]}",
        "content": content,
        "format": "markdown",
    }
