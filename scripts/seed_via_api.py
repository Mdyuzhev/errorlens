#!/usr/bin/env python3
"""Создание демо-данных через API ErrorLens.

Использование:
    python scripts/seed_via_api.py                    # localhost:8000
    python scripts/seed_via_api.py --base-url http://myserver:3000/api
    python scripts/seed_via_api.py --user admin --password Misha2026
    python scripts/seed_via_api.py --only articles
    python scripts/seed_via_api.py --only testcases
    python scripts/seed_via_api.py --only tasks
    python scripts/seed_via_api.py --only plans
    python scripts/seed_via_api.py --only issues-full # epics/stories/tasks + sprint + worklogs
    python scripts/seed_via_api.py --clean            # удалить всё перед созданием
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Данные: Папки
# ---------------------------------------------------------------------------

ARTICLE_FOLDERS: dict[str, list[str]] = {
    "Начало работы": ["Установка", "Быстрый старт"],
    "Руководство": ["Запись сессий", "AI-анализ"],
    "API Reference": ["Auth", "Sessions"],
    "Интеграции": ["TestIT", "GitLab"],
}

TESTCASE_FOLDERS: dict[str, list[str]] = {
    "Авторизация": ["Позитивные", "Негативные"],
    "API": ["Sessions", "Tasks"],
    "UI": ["Dashboard", "Tasks Board"],
    "Безопасность": ["XSS", "Injection"],
}

# ---------------------------------------------------------------------------
# Данные: 10 статей (макс. разнообразие полей)
# ---------------------------------------------------------------------------

ARTICLES: list[dict[str, Any]] = [
    {
        "title": "Добро пожаловать в ErrorLens",
        "content": "# Добро пожаловать!\n\nErrorLens — AI-powered QA платформа.\n\n## Возможности\n- Запись сессий\n- AI-анализ ошибок\n- Генерация тестов\n- Kanban задачи с JQL\n- Test Plans",
        "excerpt": "Обзор платформы ErrorLens для QA команд",
        "category": "Getting Started",
        "tags": ["overview", "introduction"],
        "status": "published",
        "folder_key": "Начало работы",
    },
    {
        "title": "Установка букмарклета",
        "content": "# Установка букмарклета\n\n## Браузеры\nChrome, Firefox, Edge, Safari.\n\n## Инструкция\n1. Settings > Bookmarklet\n2. Перетащите кнопку на панель\n3. Откройте сайт и нажмите букмарклет\n\n## Troubleshooting\n- Проверьте CSP сайта\n- Cookie должны быть разрешены",
        "excerpt": "Пошаговая установка записывающего букмарклета",
        "category": "Начало работы",
        "tags": ["install", "bookmarklet", "setup"],
        "status": "published",
        "folder_key": "Установка",
    },
    {
        "title": "Быстрый старт за 5 минут",
        "content": "# Быстрый старт\n\n1. Регистрация\n2. Установите букмарклет\n3. Запишите сессию\n4. Запустите AI-анализ\n5. Экспортируйте тесты\n\n> Весь процесс занимает менее 5 минут",
        "excerpt": "Минимальный путь от установки до первого результата",
        "category": "Начало работы",
        "tags": ["quick-start", "tutorial", "beginner"],
        "status": "published",
        "folder_key": "Быстрый старт",
    },
    {
        "title": "Режимы записи сессий",
        "content": "# Режимы записи\n\n## Full\nВсё: console, JS ошибки, HTTP, DOM.\n\n## Errors Only\nТолько JS errors и console.error.\n\n## Network Only\nHTTP запросы и ответы для API тестирования.\n\nРежим выбирается при запуске, изменить нельзя.",
        "excerpt": "Full, Errors Only, Network Only — когда какой использовать",
        "category": "Руководство",
        "tags": ["recording", "modes", "configuration"],
        "status": "published",
        "folder_key": "Запись сессий",
    },
    {
        "title": "Как читать AI-анализ",
        "content": "# Результаты AI-анализа\n\n## Структура\n- **Summary** — сводка\n- **Issues** — severity + description + root cause\n- **Statistics** — JS errors, failed HTTP, время\n\n## Severity\n| Уровень | Описание |\n|---------|----------|\n| Critical | Блокирует функционал |\n| High | Серьёзный баг |\n| Medium | Заметная проблема |\n| Low | Минорный дефект |",
        "excerpt": "Интерпретация отчётов AI-анализа ErrorLens",
        "category": "Руководство",
        "tags": ["ai", "analysis", "severity"],
        "status": "published",
        "folder_key": "AI-анализ",
    },
    {
        "title": "JWT аутентификация API",
        "content": "# JWT Auth\n\n## Login\n`POST /auth/login` → `{access_token, refresh_token}`\n\n## TTL\n- Access: 30 мин\n- Refresh: 7 дней\n\n## Refresh\n`POST /auth/refresh` с `{refresh_token}`\n\n## Ошибки\n- 401: невалидный токен\n- 403: нет прав (не admin)",
        "excerpt": "Документация по JWT токенам в ErrorLens API",
        "category": "API Reference",
        "tags": ["api", "auth", "jwt", "reference"],
        "status": "published",
        "folder_key": "Auth",
    },
    {
        "title": "Sessions API Reference",
        "content": "# Sessions API\n\n## GET /sessions\nПараметры: limit, offset, search, project_id.\nОтвет: `{items: [...], total: N}`\n\n## GET /sessions/{id}\nДетали сессии.\n\n## POST /sessions\nТело: `{url, user_agent, console_logs, network_errors}`\n\n## DELETE /sessions/{id}\n200 или 404.",
        "excerpt": "Полный справочник Sessions API",
        "category": "API Reference",
        "tags": ["api", "sessions", "reference"],
        "status": "published",
        "folder_key": "Sessions",
    },
    {
        "title": "Интеграция с TestIT",
        "content": "# TestIT Integration\n\n## Настройка\n1. TestIT > Admin > API Keys\n2. ErrorLens > Settings > Integrations > TestIT\n3. URL + API Key + Project ID > Test Connection\n\n## Маппинг\n| ErrorLens | TestIT |\n|-----------|--------|\n| title | Name |\n| steps | Steps |\n| priority | Priority |",
        "excerpt": "Подключение ErrorLens к TestIT для экспорта кейсов",
        "category": "Интеграции",
        "tags": ["testit", "integration", "export"],
        "status": "published",
        "folder_key": "TestIT",
    },
    {
        "title": "GitLab CI интеграция",
        "content": "# GitLab CI\n\n## Подключение\nSettings > Integrations > GitLab > URL + PAT\n\n## CI Pipeline\nАвтозапуск тестов → upload результатов в ErrorLens\n\n## Переменные\n- `ERRORLENS_URL` — адрес API\n- `ERRORLENS_TOKEN` — JWT токен\n\nПоддержка self-signed сертификатов.",
        "excerpt": "Настройка CI/CD пайплайна с GitLab и ErrorLens",
        "category": "Интеграции",
        "tags": ["gitlab", "ci-cd", "integration", "pipeline"],
        "status": "published",
        "folder_key": "GitLab",
    },
    {
        "title": "Горячие клавиши (draft)",
        "content": "# Горячие клавиши\n\n## Букмарклет\n- Ctrl+Shift+E — старт/стоп\n- Ctrl+Shift+S — скриншот\n\n## Дашборд\n- / — поиск\n- N — новый элемент\n- E — редактировать\n- Esc — закрыть\n\n*Документ в работе, будет дополнен.*",
        "excerpt": None,
        "category": "Руководство",
        "tags": ["hotkeys", "shortcuts"],
        "status": "draft",
        "folder_key": "Руководство",
    },
]

# ---------------------------------------------------------------------------
# Данные: 10 тест-кейсов (макс. разнообразие)
# ---------------------------------------------------------------------------

TEST_CASES: list[dict[str, Any]] = [
    {
        "title": "Login: успешный вход с валидными данными",
        "description": "Smoke-тест авторизации с корректными credentials",
        "preconditions": "Пользователь admin зарегистрирован",
        "postconditions": "Пользователь авторизован, redirect на dashboard",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Automated",
        "folder_key": "Позитивные",
        "tags": ["smoke", "auth", "positive", "p0"],
        "steps": [
            {"step": 1, "action": "Открыть /login", "expected": "Форма входа отображается"},
            {"step": 2, "action": "Ввести admin / password", "expected": "Поля заполнены"},
            {"step": 3, "action": "Нажать Submit", "expected": "Redirect на /dashboard"},
            {"step": 4, "action": "Проверить localStorage", "expected": "access_token сохранён"},
        ],
    },
    {
        "title": "Login: неверный пароль → 401",
        "description": "Негативный тест: ошибка при wrong password",
        "preconditions": "Пользователь существует",
        "postconditions": "Сообщение об ошибке, форма не очищена",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder_key": "Негативные",
        "tags": ["auth", "negative", "security"],
        "steps": [
            {"step": 1, "action": "POST /auth/login {user, wrong_pass}", "expected": "401 Unauthorized"},
            {"step": 2, "action": "Проверить body", "expected": "detail: 'Invalid credentials'"},
        ],
    },
    {
        "title": "API: GET /sessions пагинация",
        "description": "Проверка limit/offset пагинации списка сессий",
        "preconditions": "В БД >10 сессий, JWT токен валиден",
        "postconditions": "Корректная пагинация",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder_key": "Sessions",
        "tags": ["api", "sessions", "pagination"],
        "steps": [
            {"step": 1, "action": "GET /sessions?limit=5", "expected": "5 items, total > 5"},
            {"step": 2, "action": "GET /sessions?limit=5&offset=5", "expected": "Следующая страница"},
            {"step": 3, "action": "GET /sessions?limit=0", "expected": "400 Bad Request"},
        ],
    },
    {
        "title": "API: POST /tasks создание задачи со всеми полями",
        "description": "Проверка создания задачи с type, severity, environment, labels, due_date",
        "preconditions": "Проект существует, task types seeded",
        "postconditions": "Задача создана с human_id, все поля сохранены",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder_key": "Tasks",
        "tags": ["api", "tasks", "create", "positive"],
        "steps": [
            {"step": 1, "action": "POST /tasks с полным body", "expected": "201 Created"},
            {"step": 2, "action": "GET /tasks/{id}", "expected": "Все поля совпадают"},
            {"step": 3, "action": "Проверить human_id", "expected": "Формат EL-NNN"},
        ],
    },
    {
        "title": "UI: Kanban board drag & drop",
        "description": "Перетаскивание карточки между колонками Kanban",
        "preconditions": "Есть задачи в статусе To Do",
        "postconditions": "Задача переместилась в In Progress",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder_key": "Tasks Board",
        "tags": ["ui", "kanban", "drag-drop"],
        "steps": [
            {"step": 1, "action": "Открыть Tasks", "expected": "Kanban board загружен"},
            {"step": 2, "action": "Drag карточку из To Do", "expected": "Карточка захвачена"},
            {"step": 3, "action": "Drop в In Progress", "expected": "Карточка в новой колонке"},
            {"step": 4, "action": "Обновить страницу", "expected": "Статус сохранён"},
        ],
    },
    {
        "title": "UI: JQL фильтрация задач",
        "description": "Поиск задач через JQL строку",
        "preconditions": "Задачи разных типов и статусов",
        "postconditions": "Отфильтрованный список",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder_key": "Tasks Board",
        "tags": ["ui", "jql", "filter", "search"],
        "steps": [
            {"step": 1, "action": "Ввести: status = 'in_progress'", "expected": "List view активирован"},
            {"step": 2, "action": "Проверить результаты", "expected": "Только задачи In Progress"},
            {"step": 3, "action": "Добавить: AND priority = 'high'", "expected": "Уточнённый список"},
        ],
    },
    {
        "title": "Security: XSS в поле поиска",
        "description": "Проверка экранирования <script> в поисковых полях",
        "preconditions": "Авторизованный пользователь",
        "postconditions": "Скрипт не выполняется, текст экранирован",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Automated",
        "folder_key": "XSS",
        "tags": ["security", "xss", "negative", "owasp"],
        "steps": [
            {"step": 1, "action": "Ввести <script>alert(1)</script> в поиск", "expected": "Текст экранирован"},
            {"step": 2, "action": "Проверить DOM", "expected": "Нет script-тега в DOM"},
        ],
    },
    {
        "title": "Security: SQL injection в JQL",
        "description": "JQL парсер не должен пропускать SQL injection",
        "preconditions": "JQL endpoint доступен",
        "postconditions": "Ошибка парсинга, не SQL error",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Automated",
        "folder_key": "Injection",
        "tags": ["security", "sql-injection", "jql", "negative"],
        "steps": [
            {"step": 1, "action": "GET /tasks?jql=' OR 1=1--", "expected": "400 JQL parse error"},
            {"step": 2, "action": "Проверить логи", "expected": "Нет SQL error, только JQL error"},
        ],
    },
    {
        "title": "API: Refresh token ротация",
        "description": "Access token истёк → refresh → новый access token",
        "preconditions": "Валидный refresh token",
        "postconditions": "Новый access token работает",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder_key": "Позитивные",
        "tags": ["auth", "jwt", "refresh", "positive"],
        "steps": [
            {"step": 1, "action": "POST /auth/refresh {refresh_token}", "expected": "200 + new access_token"},
            {"step": 2, "action": "GET /sessions с новым токеном", "expected": "200 OK"},
            {"step": 3, "action": "GET /sessions со старым токеном", "expected": "401"},
        ],
    },
    {
        "title": "Dashboard: статистика при пустой БД",
        "description": "Дашборд не падает при отсутствии данных",
        "preconditions": "Новый проект без данных",
        "postconditions": "Нули в счётчиках, нет ошибок",
        "priority": "Low",
        "status": "Draft",
        "automation_status": "Not Applicable",
        "folder_key": "Dashboard",
        "tags": ["ui", "dashboard", "edge-case", "empty-state"],
        "steps": [
            {"step": 1, "action": "Открыть dashboard", "expected": "Страница загружена"},
            {"step": 2, "action": "Проверить счётчики", "expected": "Все = 0"},
            {"step": 3, "action": "Проверить console", "expected": "Нет JS ошибок"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Данные: 10 задач (макс. разнообразие type, status, priority, severity, env)
# ---------------------------------------------------------------------------

now = datetime.utcnow()

TASKS: list[dict[str, Any]] = [
    {
        "title": "Критический баг: белый экран после логина на iOS Safari",
        "description": "После успешной авторизации на iPhone 15 (iOS 17, Safari) — пустой белый экран. Console: `TypeError: Cannot read property 'map' of undefined` в DashboardView.",
        "status": "in_progress",
        "priority": "high",
        "type_slug": "bug",
        "severity": "critical",
        "environment": "production",
        "labels": ["ios", "safari", "blocker", "mobile"],
        "due_date": (now + timedelta(days=1)).isoformat(),
        "estimated_hours": 4.0,
        "spent_hours": 1.5,
    },
    {
        "title": "Добавить экспорт тестов в k6 формат",
        "description": "Пользователи просят генерировать k6 load-тесты из записанных HTTP сессий. Нужен новый генератор по аналогии с pytest/cypress.",
        "status": "todo",
        "priority": "medium",
        "type_slug": "story",
        "severity": None,
        "environment": None,
        "labels": ["feature", "export", "k6", "load-testing"],
        "due_date": (now + timedelta(days=14)).isoformat(),
        "estimated_hours": 16.0,
        "spent_hours": 0,
    },
    {
        "title": "Рефакторинг: вынести WebSocket в отдельный модуль",
        "description": "WebSocket manager сейчас 480 LOC. Разбить на transport, handler, protocol.",
        "status": "todo",
        "priority": "low",
        "type_slug": "task",
        "severity": None,
        "environment": None,
        "labels": ["refactoring", "tech-debt", "websocket"],
        "due_date": None,
        "estimated_hours": 8.0,
        "spent_hours": 0,
    },
    {
        "title": "Ревью: CI pipeline для autotest-demo",
        "description": "Проверить что GitLab CI pipeline корректно отправляет результаты в ErrorLens. Убедиться что flaky-тесты помечаются правильно.",
        "status": "review",
        "priority": "medium",
        "type_slug": "task",
        "severity": None,
        "environment": "staging",
        "labels": ["ci-cd", "gitlab", "review"],
        "due_date": (now + timedelta(days=3)).isoformat(),
        "estimated_hours": 2.0,
        "spent_hours": 1.0,
    },
    {
        "title": "Баг: дубликаты уведомлений при быстром переключении статуса",
        "description": "Если быстро переключить статус задачи todo→in_progress→review, приходят 2 уведомления вместо одного. Race condition в notification worker.",
        "status": "todo",
        "priority": "high",
        "type_slug": "bug",
        "severity": "major",
        "environment": "production",
        "labels": ["bug", "notifications", "race-condition"],
        "due_date": (now + timedelta(days=5)).isoformat(),
        "estimated_hours": 3.0,
        "spent_hours": 0,
    },
    {
        "title": "Epic: Аналитика и дашборды v2",
        "description": "# Аналитика v2\n\nНовая страница аналитики:\n- Графики по severity за период\n- Heatmap ошибок по URL\n- Тренды по проектам\n- Экспорт в PDF",
        "status": "todo",
        "priority": "medium",
        "type_slug": "epic",
        "severity": None,
        "environment": None,
        "labels": ["analytics", "dashboard", "v2"],
        "due_date": (now + timedelta(days=30)).isoformat(),
        "estimated_hours": 80.0,
        "spent_hours": 0,
    },
    {
        "title": "Release: v1.5.0 — JQL + Notifications",
        "description": "Релиз включает:\n- JQL парсер для фильтрации задач\n- Event Bus + уведомления\n- GitLab CI интеграция\n- Light theme fix",
        "status": "done",
        "priority": "high",
        "type_slug": "release",
        "severity": None,
        "environment": "production",
        "labels": ["release", "v1.5.0"],
        "due_date": (now - timedelta(days=2)).isoformat(),
        "estimated_hours": 0,
        "spent_hours": 0,
    },
    {
        "title": "Баг: тултип обрезается на правом краю экрана",
        "description": "При наведении на иконку типа задачи в правой колонке Kanban, тултип выходит за пределы viewport.",
        "status": "done",
        "priority": "low",
        "type_slug": "bug",
        "severity": "minor",
        "environment": "all",
        "labels": ["ui", "tooltip", "css"],
        "due_date": None,
        "estimated_hours": 0.5,
        "spent_hours": 0.25,
    },
    {
        "title": "Поддержка Playwright для генерации E2E тестов",
        "description": "Аналог Cypress генератора, но для Playwright. TypeScript output, Page Object pattern.",
        "status": "in_progress",
        "priority": "medium",
        "type_slug": "story",
        "severity": None,
        "environment": None,
        "labels": ["feature", "playwright", "export", "e2e"],
        "due_date": (now + timedelta(days=10)).isoformat(),
        "estimated_hours": 20.0,
        "spent_hours": 6.0,
    },
    {
        "title": "Документация: обновить API Reference для /tasks endpoints",
        "description": "API Reference статьи устарели после EL019 (tasks redesign). Нужно обновить: типы, статусы, workflow, JQL.",
        "status": "in_progress",
        "priority": "low",
        "type_slug": "task",
        "severity": None,
        "environment": None,
        "labels": ["docs", "api", "tasks"],
        "due_date": (now + timedelta(days=7)).isoformat(),
        "estimated_hours": 3.0,
        "spent_hours": 1.0,
    },
]

# ---------------------------------------------------------------------------
# Данные: 2 тест-плана
# ---------------------------------------------------------------------------

TEST_PLANS: list[dict[str, Any]] = [
    {
        "name": "Smoke Test Suite — Авторизация и API",
        "description": "Базовые smoke-тесты для проверки работоспособности auth и основных API.",
        "status": "active",
        "case_indices": [0, 1, 2, 3, 8],  # индексы из TEST_CASES
    },
    {
        "name": "Security Regression Pack",
        "description": "Регрессия безопасности: XSS, SQL injection, CSRF.",
        "status": "active",
        "case_indices": [6, 7],
    },
]

# ---------------------------------------------------------------------------
# Данные: 5 тестовых пользователей для issues-full
# ---------------------------------------------------------------------------

SEED_USERS: list[dict[str, str]] = [
    {"username": "dev_lead", "password": "DevLead2026!", "display_name": "Alex Petrov"},
    {"username": "frontend_dev", "password": "FrontDev2026!", "display_name": "Maria Ivanova"},
    {"username": "backend_dev", "password": "BackDev2026!", "display_name": "Dmitry Sokolov"},
    {"username": "qa_engineer", "password": "QaEng2026!", "display_name": "Elena Kuznetsova"},
    {"username": "pm_user", "password": "PmUser2026!", "display_name": "Sergei Volkov"},
]


# ---------------------------------------------------------------------------
# API клиент
# ---------------------------------------------------------------------------


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.token: str | None = None
        self.project_id: str | None = None
        self.task_types: dict[str, str] = {}  # slug → id

    def login(self, username: str, password: str) -> None:
        r = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password},
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        print(f"  Logged in as {username}")

    def ensure_project(self, force_recreate: bool = False) -> str:
        r = self.get("/projects")
        if r.status_code == 200:
            projects = r.json()
            if projects and force_recreate:
                for p in projects:
                    print(f"  Deleting project: {p['name']} ({p['id']})")
                    self.delete(f"/projects/{p['id']}")
                projects = []
            if projects:
                self.project_id = projects[0]["id"]
                print(f"  Using project: {projects[0]['name']} (key={projects[0].get('key')})")
                return self.project_id

        r = self.post("/projects", json={
            "name": "ErrorLens Demo",
            "description": "Demo project for QA platform",
            "key": "EL",
        })
        r.raise_for_status()
        data = r.json()
        self.project_id = data["id"]
        print(f"  Created project: ErrorLens Demo (key={data.get('key')})")
        return self.project_id

    def load_task_types(self) -> None:
        r = self.get(f"/task-settings/types?project_id={self.project_id}")
        if r.status_code == 200:
            for t in r.json():
                self.task_types[t["slug"]] = t["id"]
        if not self.task_types:
            # seed defaults
            r = self.post(f"/task-settings/seed?project_id={self.project_id}")
            if r.status_code in (200, 201):
                r2 = self.get(f"/task-settings/types?project_id={self.project_id}")
                if r2.status_code == 200:
                    for t in r2.json():
                        self.task_types[t["slug"]] = t["id"]
        print(f"  Task types: {list(self.task_types.keys())}")

    def get(self, path: str, **kw: Any) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", **kw)

    def post(self, path: str, **kw: Any) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", **kw)

    def put(self, path: str, **kw: Any) -> requests.Response:
        return self.session.put(f"{self.base_url}{path}", **kw)

    def patch(self, path: str, **kw: Any) -> requests.Response:
        return self.session.patch(f"{self.base_url}{path}", **kw)

    def delete(self, path: str, **kw: Any) -> requests.Response:
        return self.session.delete(f"{self.base_url}{path}", **kw)


# ---------------------------------------------------------------------------
# Создание данных
# ---------------------------------------------------------------------------


def create_folders(api: ApiClient, endpoint: str, tree: dict[str, list[str]]) -> dict[str, str]:
    folder_map: dict[str, str] = {}
    for parent, children in tree.items():
        r = api.post(endpoint, json={"name": parent, "project_id": api.project_id})
        if r.status_code >= 400:
            print(f"    WARN folder '{parent}': {r.status_code}")
            continue
        pid = r.json()["id"]
        folder_map[parent] = pid
        for child in children:
            r2 = api.post(endpoint, json={"name": child, "parent_id": pid, "project_id": api.project_id})
            if r2.status_code >= 400:
                print(f"    WARN folder '{child}': {r2.status_code}")
                continue
            folder_map[child] = r2.json()["id"]
    print(f"  Created {len(folder_map)} folders ({endpoint})")
    return folder_map


def create_articles(api: ApiClient, folder_map: dict[str, str]) -> int:
    count = 0
    for art in ARTICLES:
        body: dict[str, Any] = {
            "title": art["title"],
            "content": art["content"],
            "excerpt": art.get("excerpt"),
            "category": art.get("category"),
            "tags": art.get("tags", []),
            "status": art.get("status", "draft"),
            "project_id": api.project_id,
        }
        fk = art.get("folder_key")
        if fk and fk in folder_map:
            body["folder_id"] = folder_map[fk]
        r = api.post("/articles", json=body)
        if r.status_code >= 400:
            print(f"    WARN article '{art['title'][:40]}': {r.status_code} {r.text[:80]}")
            continue
        count += 1
    print(f"  Created {count}/{len(ARTICLES)} articles")
    return count


def create_testcases(api: ApiClient, folder_map: dict[str, str]) -> list[str]:
    ids: list[str] = []
    for tc in TEST_CASES:
        body: dict[str, Any] = {
            "title": tc["title"],
            "description": tc.get("description"),
            "preconditions": tc.get("preconditions"),
            "postconditions": tc.get("postconditions"),
            "priority": tc.get("priority", "Medium"),
            "status": tc.get("status", "Draft"),
            "automation_status": tc.get("automation_status", "Manual"),
            "tags": tc.get("tags", []),
            "steps": tc.get("steps", []),
            "project_id": api.project_id,
        }
        fk = tc.get("folder_key")
        if fk and fk in folder_map:
            body["folder_id"] = folder_map[fk]
        r = api.post("/testcases", json=body)
        if r.status_code >= 400:
            print(f"    WARN testcase '{tc['title'][:40]}': {r.status_code} {r.text[:80]}")
            continue
        ids.append(r.json()["id"])
    print(f"  Created {len(ids)}/{len(TEST_CASES)} test cases")
    return ids


def create_tasks(api: ApiClient) -> list[str]:
    ids: list[str] = []
    for task in TASKS:
        body: dict[str, Any] = {
            "title": task["title"],
            "description": task.get("description"),
            "status": task.get("status", "todo"),
            "priority": task.get("priority", "medium"),
            "labels": task.get("labels", []),
            "project_id": api.project_id,
        }
        if task.get("severity"):
            body["severity"] = task["severity"]
        if task.get("environment"):
            body["environment"] = task["environment"]
        if task.get("due_date"):
            body["due_date"] = task["due_date"]
        if task.get("estimated_hours"):
            body["estimated_hours"] = task["estimated_hours"]
        if task.get("spent_hours"):
            body["spent_hours"] = task["spent_hours"]

        slug = task.get("type_slug")
        if slug and slug in api.task_types:
            body["type_id"] = api.task_types[slug]

        r = api.post("/tasks", json=body)
        if r.status_code >= 400:
            print(f"    WARN task '{task['title'][:40]}': {r.status_code} {r.text[:80]}")
            continue
        ids.append(r.json()["id"])
    print(f"  Created {len(ids)}/{len(TASKS)} tasks")
    return ids


def create_test_plans(api: ApiClient, tc_ids: list[str]) -> None:
    for plan_data in TEST_PLANS:
        r = api.post("/api/v1/test-plans", json={
            "name": plan_data["name"],
            "description": plan_data.get("description"),
            "status": plan_data.get("status", "draft"),
            "project_id": api.project_id,
        })
        if r.status_code >= 400:
            print(f"    WARN plan '{plan_data['name'][:40]}': {r.status_code} {r.text[:80]}")
            continue
        plan_id = r.json()["id"]

        # add cases
        case_ids = [tc_ids[i] for i in plan_data["case_indices"] if i < len(tc_ids)]
        if case_ids:
            api.post(f"/api/v1/test-plans/{plan_id}/cases", json={"testcase_ids": case_ids})

        # create a run
        r2 = api.post(f"/api/v1/test-plans/{plan_id}/runs", json={"name": f"Run #{1}"})
        if r2.status_code >= 400:
            continue
        run_id = r2.json()["id"]

        # record some results
        results = ["passed", "passed", "failed", "passed", "skipped"]
        for i, cid in enumerate(case_ids):
            status = results[i % len(results)]
            comment = f"Auto-seeded result: {status}" if status != "passed" else None
            api.put(f"/api/v1/test-plans/runs/{run_id}/results/{cid}", json={
                "status": status,
                "comment": comment,
            })

    print(f"  Created {len(TEST_PLANS)} test plans with runs")


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------


def seed_users(api: ApiClient) -> dict[str, str]:
    """Create test users via /admin/users, fallback to /auth/register.

    Returns mapping username -> user_id.
    """
    user_map: dict[str, str] = {}

    # First, try to get existing users
    r = api.get("/admin/users")
    existing: dict[str, str] = {}
    if r.status_code == 200:
        for u in r.json():
            existing[u["username"]] = u["id"]

    for u in SEED_USERS:
        if u["username"] in existing:
            user_map[u["username"]] = existing[u["username"]]
            print(f"    User '{u['username']}' already exists")
            continue

        # Try admin endpoint first
        r = api.post("/admin/users", json={
            "username": u["username"],
            "password": u["password"],
            "is_admin": False,
        })
        if r.status_code in (200, 201):
            user_map[u["username"]] = r.json()["id"]
            print(f"    Created user '{u['username']}' via /admin/users")
            continue

        # Fallback to /auth/register
        r = api.post("/auth/register", json={
            "username": u["username"],
            "password": u["password"],
        })
        if r.status_code in (200, 201):
            data = r.json()
            uid = data.get("id") or data.get("user_id", "")
            user_map[u["username"]] = uid
            print(f"    Created user '{u['username']}' via /auth/register")
            continue

        print(f"    WARN: failed to create user '{u['username']}': {r.status_code}")

    print(f"  Seeded {len(user_map)}/{len(SEED_USERS)} users")
    return user_map


def seed_issues_full(api: ApiClient, user_map: dict[str, str]) -> None:
    """Create full issue hierarchy: epics, stories, tasks, sprint, worklogs, bugs."""
    if not api.task_types:
        api.load_task_types()

    users = list(user_map.values())
    usernames = list(user_map.keys())

    # ---------------------------------------------------------------
    # Sprint (today-7 .. today+7)
    # ---------------------------------------------------------------
    print("\n  Creating sprint...")
    sprint_start = (now - timedelta(days=7)).date().isoformat()
    sprint_end = (now + timedelta(days=7)).date().isoformat()
    r = api.post("/api/v1/sprints", json={
        "project_id": api.project_id,
        "name": "Sprint 1 — MVP",
        "goal": "Deliver core features for demo",
        "start_date": sprint_start,
        "end_date": sprint_end,
    })
    sprint_id = None
    if r.status_code in (200, 201):
        sprint_id = r.json().get("id")
        print(f"    Sprint created: {sprint_id}")
    else:
        print(f"    WARN sprint: {r.status_code} {r.text[:80]}")

    # ---------------------------------------------------------------
    # Helper: create a task
    # ---------------------------------------------------------------
    created_ids: list[str] = []

    def _create_task(
        title: str,
        type_slug: str,
        status: str = "todo",
        priority: str = "medium",
        parent_id: str | None = None,
        assignee_id: str | None = None,
        story_points: int | None = None,
        in_sprint: bool = False,
        **extra: Any,
    ) -> str | None:
        body: dict[str, Any] = {
            "title": title,
            "status": status,
            "priority": priority,
            "project_id": api.project_id,
        }
        slug = type_slug
        if slug in api.task_types:
            body["type_id"] = api.task_types[slug]
        if parent_id:
            body["parent_id"] = parent_id
        if assignee_id:
            body["assignee_id"] = assignee_id
        if story_points is not None:
            body["story_points"] = story_points
        if in_sprint and sprint_id:
            body["sprint_id"] = sprint_id
        body.update(extra)

        resp = api.post("/tasks", json=body)
        if resp.status_code >= 400:
            print(f"    WARN task '{title[:40]}': {resp.status_code} {resp.text[:80]}")
            return None
        tid = resp.json()["id"]
        created_ids.append(tid)
        return tid

    # ---------------------------------------------------------------
    # Epic 1: Platform Core
    # ---------------------------------------------------------------
    print("\n  Creating epics & stories & tasks...")
    epic1 = _create_task(
        "Epic: Platform Core — Auth & Projects",
        "epic", status="in_progress", priority="high",
        story_points=21,
    )

    if epic1:
        story1a = _create_task(
            "Story: JWT authentication flow",
            "story", status="done", priority="high",
            parent_id=epic1, assignee_id=users[2] if len(users) > 2 else None,
            story_points=8, in_sprint=True,
        )
        if story1a:
            _create_task(
                "Implement /auth/login endpoint",
                "task", status="done", priority="high",
                parent_id=story1a, assignee_id=users[2] if len(users) > 2 else None,
                story_points=3, in_sprint=True,
                estimated_hours=4.0, spent_hours=3.5,
            )
            _create_task(
                "Implement /auth/refresh endpoint",
                "task", status="done", priority="medium",
                parent_id=story1a, assignee_id=users[2] if len(users) > 2 else None,
                story_points=2, in_sprint=True,
                estimated_hours=2.0, spent_hours=2.0,
            )
            _create_task(
                "Add JWT middleware + role checks",
                "task", status="done", priority="high",
                parent_id=story1a, assignee_id=users[0] if users else None,
                story_points=3, in_sprint=True,
                estimated_hours=3.0, spent_hours=4.0,
            )

        story1b = _create_task(
            "Story: Multi-tenant project isolation",
            "story", status="in_progress", priority="high",
            parent_id=epic1, assignee_id=users[0] if users else None,
            story_points=13, in_sprint=True,
        )
        if story1b:
            _create_task(
                "Add project_id filtering to all queries",
                "task", status="done", priority="high",
                parent_id=story1b, assignee_id=users[2] if len(users) > 2 else None,
                story_points=5, in_sprint=True,
                estimated_hours=6.0, spent_hours=5.0,
            )
            _create_task(
                "Implement check_project_access middleware",
                "task", status="in_progress", priority="high",
                parent_id=story1b, assignee_id=users[0] if users else None,
                story_points=5, in_sprint=True,
                estimated_hours=4.0, spent_hours=2.0,
            )
            _create_task(
                "Write integration tests for isolation",
                "task", status="todo", priority="medium",
                parent_id=story1b, assignee_id=users[3] if len(users) > 3 else None,
                story_points=3, in_sprint=True,
                estimated_hours=3.0,
            )

    # ---------------------------------------------------------------
    # Epic 2: QA Automation
    # ---------------------------------------------------------------
    epic2 = _create_task(
        "Epic: QA Automation — Test Plans & AI",
        "epic", status="todo", priority="medium",
        story_points=34,
    )

    if epic2:
        story2a = _create_task(
            "Story: Test plan execution engine",
            "story", status="in_progress", priority="medium",
            parent_id=epic2, assignee_id=users[3] if len(users) > 3 else None,
            story_points=13, in_sprint=True,
        )
        if story2a:
            _create_task(
                "Design test run state machine",
                "task", status="done", priority="high",
                parent_id=story2a, assignee_id=users[0] if users else None,
                story_points=5, in_sprint=True,
                estimated_hours=4.0, spent_hours=3.0,
            )
            _create_task(
                "Implement run results aggregation",
                "task", status="in_progress", priority="medium",
                parent_id=story2a, assignee_id=users[3] if len(users) > 3 else None,
                story_points=5, in_sprint=True,
                estimated_hours=6.0, spent_hours=2.5,
            )

        story2b = _create_task(
            "Story: AI-powered test generation",
            "story", status="todo", priority="medium",
            parent_id=epic2, assignee_id=users[1] if len(users) > 1 else None,
            story_points=21,
        )
        if story2b:
            _create_task(
                "Integrate Claude API for test generation",
                "task", status="todo", priority="medium",
                parent_id=story2b, assignee_id=users[1] if len(users) > 1 else None,
                story_points=8,
                estimated_hours=10.0,
            )
            _create_task(
                "Build prompt templates for different frameworks",
                "task", status="todo", priority="low",
                parent_id=story2b, assignee_id=users[1] if len(users) > 1 else None,
                story_points=5,
                estimated_hours=6.0,
            )
            _create_task(
                "Add output validators for generated tests",
                "task", status="todo", priority="medium",
                parent_id=story2b, assignee_id=users[3] if len(users) > 3 else None,
                story_points=8,
                estimated_hours=8.0,
            )

    # ---------------------------------------------------------------
    # 2 standalone Bugs
    # ---------------------------------------------------------------
    print("  Creating standalone bugs...")
    _create_task(
        "Bug: Kanban drag-drop loses card on slow network",
        "bug", status="todo", priority="high",
        assignee_id=users[1] if len(users) > 1 else None,
        in_sprint=True, severity="major", environment="production",
        labels=["bug", "kanban", "ux"],
        estimated_hours=3.0,
    )
    _create_task(
        "Bug: JQL parser crashes on empty parentheses",
        "bug", status="in_progress", priority="medium",
        assignee_id=users[2] if len(users) > 2 else None,
        in_sprint=True, severity="minor", environment="staging",
        labels=["bug", "jql", "parser"],
        estimated_hours=2.0, spent_hours=0.5,
    )

    print(f"  Created {len(created_ids)} issues total")

    # ---------------------------------------------------------------
    # WorkLog entries (15 entries from 4 users)
    # ---------------------------------------------------------------
    print("\n  Creating work log entries...")
    wl_count = 0
    # Pick tasks that have spent_hours (they should exist)
    log_targets = [tid for tid in created_ids[:12] if tid]
    log_users = users[:4] if len(users) >= 4 else users

    worklog_data = [
        (0, -6, 2.0, "Initial research and design"),
        (1, -5, 3.0, "Endpoint implementation"),
        (0, -5, 1.5, "Code review comments"),
        (2, -4, 4.0, "Full day on auth flow"),
        (1, -4, 2.5, "Frontend integration"),
        (3, -3, 1.0, "Test case writing"),
        (0, -3, 3.0, "Refactoring middleware"),
        (2, -2, 2.0, "Bug fix in token refresh"),
        (3, -2, 4.0, "Integration test suite"),
        (1, -1, 1.5, "UI polish and fixes"),
        (0, -1, 2.0, "Sprint review prep"),
        (2, 0, 3.0, "Query optimization"),
        (3, 0, 2.0, "Regression testing"),
        (1, 0, 1.0, "CSS variable migration"),
        (0, 0, 1.5, "Documentation update"),
    ]

    for user_idx, day_offset, hours, comment in worklog_data:
        if not log_targets or not log_users:
            break
        uid = log_users[user_idx % len(log_users)]
        tid = log_targets[wl_count % len(log_targets)]
        log_date = (now + timedelta(days=day_offset)).date().isoformat()

        r = api.post("/api/v1/work-logs", json={
            "issue_id": tid,
            "hours": hours,
            "log_date": log_date,
            "comment": comment,
        })
        if r.status_code in (200, 201):
            wl_count += 1
        else:
            print(f"    WARN worklog: {r.status_code} {r.text[:60]}")

    print(f"  Created {wl_count}/15 work log entries")


def clean_entity(api: ApiClient, list_path: str, delete_path: str, label: str) -> None:
    params: dict[str, Any] = {"limit": 200}
    if api.project_id:
        params["project_id"] = api.project_id
    r = api.get(list_path, params=params)
    if r.status_code != 200:
        return
    data = r.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    for item in items:
        api.delete(f"{delete_path}/{item['id']}")
    if items:
        print(f"  Deleted {len(items)} {label}")


def clean_folders(api: ApiClient, endpoint: str, label: str) -> None:
    params = {"project_id": api.project_id} if api.project_id else {}
    r = api.get(endpoint, params=params)
    if r.status_code != 200:
        return
    data = r.json()
    folders = data.get("folders", data) if isinstance(data, dict) else data
    leaf_ids, parent_ids = [], []
    for f in folders:
        parent_ids.append(f["id"])
        for c in f.get("children", []):
            leaf_ids.append(c["id"])
    for fid in leaf_ids + parent_ids:
        api.delete(f"{endpoint}/{fid}")
    total = len(leaf_ids) + len(parent_ids)
    if total:
        print(f"  Deleted {total} {label} folders")


def clean_all(api: ApiClient) -> None:
    print("\nCleaning existing data...")
    clean_entity(api, "/api/v1/test-plans", "/api/v1/test-plans", "test plans")
    clean_entity(api, "/tasks", "/tasks", "tasks")
    clean_entity(api, "/testcases", "/testcases", "test cases")
    clean_entity(api, "/articles", "/articles", "articles")
    clean_folders(api, "/testcases/folders", "testcase")
    clean_folders(api, "/articles/folders", "article")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ErrorLens demo data via API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument(
        "--only",
        choices=["articles", "testcases", "tasks", "plans", "issues-full"],
    )
    parser.add_argument("--clean", action="store_true", help="Delete existing data first")
    args = parser.parse_args()

    api = ApiClient(args.base_url)

    print(f"Connecting to {args.base_url}...")
    try:
        api.login(args.user, args.password)
    except Exception as e:
        print(f"ERROR: login failed: {e}")
        sys.exit(1)

    try:
        api.ensure_project(force_recreate=args.clean)
    except Exception as e:
        print(f"WARN: project: {e}")

    if args.clean:
        clean_all(api)

    api.load_task_types()

    do_all = args.only is None
    tc_ids: list[str] = []

    if do_all or args.only == "articles":
        print("\n--- Articles ---")
        af = create_folders(api, "/articles/folders", ARTICLE_FOLDERS)
        create_articles(api, af)

    if do_all or args.only == "testcases":
        print("\n--- Test Cases ---")
        tcf = create_folders(api, "/testcases/folders", TESTCASE_FOLDERS)
        tc_ids = create_testcases(api, tcf)

    if do_all or args.only == "tasks":
        print("\n--- Tasks ---")
        create_tasks(api)

    if do_all or args.only == "plans":
        print("\n--- Test Plans ---")
        if not tc_ids:
            # need testcase ids for plans
            r = api.get("/testcases", params={"limit": 20, "project_id": api.project_id})
            if r.status_code == 200:
                data = r.json()
                items = data.get("items", data) if isinstance(data, dict) else data
                tc_ids = [i["id"] for i in items]
        if tc_ids:
            create_test_plans(api, tc_ids)
        else:
            print("  SKIP: no test cases for plans")

    if args.only == "issues-full":
        print("\n--- Issues Full (epics, stories, tasks, sprint, worklogs, bugs) ---")
        print("\n  Seeding users...")
        user_map = seed_users(api)
        seed_issues_full(api, user_map)

    print("\nDone!")


if __name__ == "__main__":
    main()
