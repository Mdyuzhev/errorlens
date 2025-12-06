"""TestIt test case generator from recorded HTTP sessions."""

import json
import re
from datetime import datetime
from urllib.parse import urlparse


class TestItGenerator:
    """Generate TestIt-compatible test cases from recorded requests."""

    # Mapping HTTP methods to actions (Russian)
    METHOD_ACTIONS = {
        "GET": "Получить",
        "POST": "Создать",
        "PUT": "Обновить",
        "PATCH": "Изменить",
        "DELETE": "Удалить",
    }

    # Mapping URL paths to business entities
    ENTITY_PATTERNS = {
        r"/auth|/login|/logout": "авторизация",
        r"/users?": "пользователь",
        r"/orders?": "заказ",
        r"/products?": "товар",
        r"/cart": "корзина",
        r"/payment": "оплата",
        r"/session": "сессия",
        r"/pet": "питомец",
        r"/store": "магазин",
    }

    # Mapping severity to TestIt priority
    SEVERITY_TO_PRIORITY = {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }

    def __init__(self, session_data: dict, analysis: dict | None = None):
        """
        Initialize generator.

        Args:
            session_data: Session with recorded_requests, console_logs, etc.
            analysis: Optional AI analysis result.
        """
        self.session = session_data
        self.analysis = analysis or {}
        self.recorded_requests = session_data.get("recorded_requests", [])
        self.base_url = self._extract_base_url()

    def _extract_base_url(self) -> str:
        """Extract base URL from first request."""
        if self.recorded_requests:
            first_req = self.recorded_requests[0]
            # Handle both dict and nested request structure
            if isinstance(first_req, dict):
                request = first_req.get("request", first_req)
                first_url = request.get("url", "")
            else:
                first_url = ""
            parsed = urlparse(first_url)
            return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else ""
        return self.session.get("url", "")

    def _get_entity_name(self, path: str) -> str:
        """Determine business entity from URL path."""
        for pattern, entity in self.ENTITY_PATTERNS.items():
            if re.search(pattern, path, re.IGNORECASE):
                return entity

        # Fallback: extract from path
        parts = [p for p in path.split("/") if p and not p.isdigit()]
        if parts:
            return parts[-1].rstrip("s")  # Remove plural 's'
        return "ресурс"

    def _request_to_action(self, request: dict) -> str:
        """Convert HTTP request to human-readable action."""
        method = request.get("method", "GET")
        url = request.get("url", "")
        path = urlparse(url).path

        action_verb = self.METHOD_ACTIONS.get(method, "Выполнить")
        entity = self._get_entity_name(path)

        return f"{action_verb} {entity}"

    def _generate_expected_result(self, response: dict, is_error: bool) -> str:
        """Generate expected result from response."""
        status = response.get("status", 200)

        if is_error:
            return f"Ошибка: статус {status}"

        if status == 200:
            return "Успешный ответ (200 OK)"
        elif status == 201:
            return "Ресурс создан (201 Created)"
        elif status == 204:
            return "Успешно без содержимого (204 No Content)"
        else:
            return f"Статус ответа: {status}"

    def _extract_test_data(self, request: dict) -> str:
        """Extract test data from request body."""
        body = request.get("body", "")

        if not body:
            return ""

        # Handle non-string body
        if not isinstance(body, str):
            try:
                body = json.dumps(body, ensure_ascii=False)
            except (TypeError, ValueError):
                body = str(body)

        # Truncate long bodies
        if len(body) > 500:
            body = body[:500] + "..."

        # Mask sensitive data
        body = re.sub(r'"password"\s*:\s*"[^"]*"', '"password": "***"', body)
        body = re.sub(r'"token"\s*:\s*"[^"]*"', '"token": "***"', body)

        return body

    def _detect_preconditions(self) -> list[str]:
        """Auto-detect preconditions from session."""
        preconditions = []

        # Check for auth in first few requests
        for req in self.recorded_requests[:5]:
            if isinstance(req, dict):
                request = req.get("request", req)
            else:
                continue

            headers = request.get("headers", {})
            url = request.get("url", "")

            if "authorization" in str(headers).lower():
                preconditions.append("Пользователь авторизован в системе")
                break
            if "/login" in url or "/auth" in url:
                preconditions.append("Учётные данные пользователя известны")
                break

        if not preconditions:
            preconditions.append("Система доступна")

        if self.base_url:
            preconditions.append(f"Базовый URL: {self.base_url}")

        return preconditions

    def _determine_priority(self) -> str:
        """Determine test case priority."""
        severity = self.analysis.get("severity", "medium")
        return self.SEVERITY_TO_PRIORITY.get(severity, "Medium")

    def _generate_tags(self) -> list[str]:
        """Generate tags from session data."""
        tags = ["api", "automated"]

        # Add tags based on URLs
        for req in self.recorded_requests:
            if isinstance(req, dict):
                request = req.get("request", req)
            else:
                continue

            url = request.get("url", "")
            path = urlparse(url).path.lower()

            if "/auth" in path or "/login" in path:
                tags.append("auth")
            if "/order" in path:
                tags.append("orders")
            if "/product" in path:
                tags.append("products")
            if "/user" in path:
                tags.append("users")
            if "/pet" in path:
                tags.append("pet")

        # Add error tag if session has errors
        if self.session.get("has_errors"):
            tags.append("regression")

        return list(set(tags))[:5]  # Max 5 unique tags

    def _generate_title(self) -> str:
        """Generate test case title."""
        if self.analysis.get("summary"):
            # Clean up AI summary for title
            summary = self.analysis["summary"]
            if len(summary) > 80:
                summary = summary[:77] + "..."
            return f"Проверка: {summary}"

        # Fallback: generate from requests
        if self.recorded_requests:
            first_req = self.recorded_requests[0]
            if isinstance(first_req, dict):
                request = first_req.get("request", first_req)
            else:
                request = {}
            action = self._request_to_action(request)
            return f"Тест: {action}"

        return "Тест записанного сценария"

    def generate(self) -> dict:
        """Generate TestIt test case structure."""
        steps = []
        has_error = False

        for req in self.recorded_requests:
            if isinstance(req, dict):
                request = req.get("request", req)
                response = req.get("response", {})
            else:
                continue

            status = response.get("status", 200)
            is_error = status >= 400

            if is_error:
                has_error = True

            # Generate step
            method = request.get("method", "GET")
            url = request.get("url", "")
            path = urlparse(url).path

            step = {
                "action": f"{self._request_to_action(request)}\n\n" f"`{method} {path}`",
                "expected": self._generate_expected_result(response, is_error),
                "testData": self._extract_test_data(request),
            }
            steps.append(step)

        # Generate postconditions based on outcome
        if has_error:
            postconditions = "Ошибка зафиксирована и требует исправления"
        else:
            postconditions = "Все операции выполнены успешно"

        test_case = {
            "name": self._generate_title(),
            "description": self.analysis.get(
                "probable_cause",
                "Автоматически сгенерированный тест-кейс из записи сессии ErrorLens",
            ),
            "state": "Ready",
            "priority": self._determine_priority(),
            "preconditions": "\n".join(self._detect_preconditions()),
            "postconditions": postconditions,
            "steps": steps,
            "tags": self._generate_tags(),
            "automationStatus": "Automated" if self.recorded_requests else "NotAutomated",
            "links": [
                {
                    "title": "ErrorLens Session",
                    "url": f"/sessions/{self.session.get('id', '')}",
                }
            ],
        }

        return test_case

    def generate_testit_json(self) -> str:
        """Generate TestIt import JSON."""
        test_case = self.generate()

        export_data = {
            "testCases": [test_case],
            "exportedAt": datetime.utcnow().isoformat(),
            "source": "ErrorLens",
        }

        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def generate_testit_xml(self) -> str:
        """Generate TestIt import XML."""
        test_case = self.generate()

        # Build XML manually for control
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<testCases>",
            "  <testCase>",
            f'    <name><![CDATA[{test_case["name"]}]]></name>',
            f'    <description><![CDATA[{test_case["description"]}]]></description>',
            f'    <state>{test_case["state"]}</state>',
            f'    <priority>{test_case["priority"]}</priority>',
            f'    <preconditions><![CDATA[{test_case["preconditions"]}]]></preconditions>',
            f'    <postconditions><![CDATA[{test_case["postconditions"]}]]></postconditions>',
            "    <steps>",
        ]

        for i, step in enumerate(test_case["steps"], 1):
            xml_lines.extend(
                [
                    f'      <step position="{i}">',
                    f'        <action><![CDATA[{step["action"]}]]></action>',
                    f'        <expected><![CDATA[{step["expected"]}]]></expected>',
                    f'        <testData><![CDATA[{step["testData"]}]]></testData>',
                    "      </step>",
                ]
            )

        xml_lines.extend(
            [
                "    </steps>",
                "    <tags>",
            ]
        )

        for tag in test_case["tags"]:
            xml_lines.append(f"      <tag>{tag}</tag>")

        xml_lines.extend(
            [
                "    </tags>",
                f'    <automationStatus>{test_case["automationStatus"]}</automationStatus>',
                "  </testCase>",
                "</testCases>",
            ]
        )

        return "\n".join(xml_lines)

    def generate_markdown(self) -> str:
        """Generate Markdown representation for preview."""
        tc = self.generate()

        lines = [
            f"# {tc['name']}",
            "",
            f"**Приоритет:** {tc['priority']}  ",
            f"**Статус:** {tc['state']}  ",
            f"**Автоматизация:** {tc['automationStatus']}",
            "",
            "## Описание",
            tc["description"],
            "",
            "## Предусловия",
            tc["preconditions"],
            "",
            "## Шаги",
            "",
            "| # | Действие | Ожидаемый результат | Тестовые данные |",
            "|---|----------|---------------------|-----------------|",
        ]

        for i, step in enumerate(tc["steps"], 1):
            action = step["action"].replace("\n", " ").replace("|", "\\|")
            expected = step["expected"].replace("|", "\\|")
            test_data = step["testData"][:50].replace("|", "\\|") if step["testData"] else "-"
            lines.append(f"| {i} | {action} | {expected} | {test_data} |")

        lines.extend(
            [
                "",
                "## Постусловия",
                tc["postconditions"],
                "",
                f"**Теги:** {', '.join(tc['tags'])}",
                "",
                "---",
                f"*Сгенерировано ErrorLens: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            ]
        )

        return "\n".join(lines)


def generate_testit_testcase(
    session_data: dict, analysis: dict = None, format: str = "json"
) -> str:
    """
    Generate TestIt test case from session.

    Args:
        session_data: Session with recorded requests
        analysis: Optional AI analysis
        format: Output format ('json', 'xml', 'markdown')

    Returns:
        Formatted test case string
    """
    generator = TestItGenerator(session_data, analysis)

    if format == "xml":
        return generator.generate_testit_xml()
    elif format == "markdown":
        return generator.generate_markdown()
    else:
        return generator.generate_testit_json()
