#!/usr/bin/env python3
"""
ErrorLens Project Seeder — EL070 v3
ПОЛНАЯ ОЧИСТКА + пересоздание в СУЩЕСТВУЮЩЕМ проекте admin.

Проект: 9ddfd925-9728-4224-8a3d-13a6e2e01719 (ErrorLens, key=EL, owner=admin)
Запуск: python3 scripts/seed_project.py
"""

import json, os, sys, uuid
import requests

BASE_URL  = os.getenv("EL_URL",      "http://192.168.1.74:3000/api")
USERNAME  = os.getenv("EL_USERNAME", "admin")
PASSWORD  = os.getenv("EL_PASSWORD", "Misha2026")
PROJECT_ID = "9ddfd925-9728-4224-8a3d-13a6e2e01719"

# nginx strips /api/ → backend root; /api/api/v1/ → backend /api/v1/
TASKS_URL       = f"{BASE_URL}/tasks"
ARTICLES_URL    = f"{BASE_URL}/articles"
TESTCASES_URL   = f"{BASE_URL}/testcases"
TC_FOLDERS_URL  = f"{BASE_URL}/testcases/folders"
ART_FOLDERS_URL = f"{BASE_URL}/articles/folders"
PROJECTS_URL    = f"{BASE_URL}/projects"
SETTINGS_URL    = f"{BASE_URL}/task-settings"
TEST_PLANS_URL  = f"{BASE_URL}/v1/test-plans"
SPRINTS_URL     = f"{BASE_URL}/api/v1/sprints"
COMPONENTS_URL  = f"{BASE_URL}/api/v1/components"
PECHKIN_URL     = f"{BASE_URL}/api/v1/pechkin"

class ELClient:
    def __init__(self):
        self.s = requests.Session()

    def login(self):
        r = self.s.post(f"{BASE_URL}/auth/login",
                        json={"username": USERNAME, "password": PASSWORD}, timeout=15)
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        print(f"[AUTH] Logged in as {USERNAME}")

    def get(self, url, **kw):    return self.s.get(url, timeout=15, **kw)
    def post(self, url, **kw):   return self.s.post(url, timeout=15, **kw)
    def put(self, url, **kw):    return self.s.put(url, timeout=15, **kw)
    def delete(self, url, **kw): return self.s.delete(url, timeout=15, **kw)

c = ELClient()
TYPES = {}       # slug → id
COMPONENTS = {}  # name → id
EPICS = {}       # key → task_id
STORIES = {}     # key → task_id
BUGS = {}        # key → task_id
SPRINTS = {}     # label → sprint_id
TC_FOLDERS = {}  # name → folder_id
ART_FOLDERS = {} # name → folder_id


def uid(): return str(uuid.uuid4())[:8]


def ok(r, label=""):
    if not r.ok:
        print(f"  [WARN] {label}: HTTP {r.status_code} — {r.text[:120]}")
        return None
    try: return r.json()
    except: return {}


# ─── Content helpers ──────────────────────────────────────────────────────────

def grid(*blocks):
    return json.dumps({
        "version": "grid-1",
        "rows": [{"id": uid(), "columns": [{"id": uid(), "span": 12,
            "content": {"type": "doc", "content": list(blocks)}}]}]
    })

def h1(t): return {"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": t}]}
def h2(t): return {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": t}]}
def h3(t): return {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": t}]}
def p(t):  return {"type": "paragraph", "content": [{"type": "text", "text": t}]}
def ul(*items): return {"type": "bulletList", "content": [
    {"type": "listItem", "content": [p(i)]} for i in items]}
def code(t, lang="python"): return {"type": "codeBlock", "attrs": {"language": lang},
    "content": [{"type": "text", "text": t}]}


# ════════════════════════════════════════════════════════════════════════════
# SECTION 0 — ПОЛНАЯ ОЧИСТКА
# ════════════════════════════════════════════════════════════════════════════

def cleanup():
    print("\n[0] CLEANUP ─────────────────────────────────────────────────────")
    pid = PROJECT_ID

    # — Tasks (все: epics, stories, bugs, tasks) —
    r = c.get(TASKS_URL, params={"project_id": pid, "limit": 500})
    tasks = r.json() if r.ok else []
    tasks = tasks if isinstance(tasks, list) else tasks.get("items", [])
    deleted = 0
    for t in tasks:
        if c.delete(f"{TASKS_URL}/{t['id']}").ok:
            deleted += 1
    print(f"  Tasks deleted: {deleted}/{len(tasks)}")

    # — Sprints —
    r = c.get(SPRINTS_URL, params={"project_id": pid})
    if r.ok:
        sprints = r.json() if isinstance(r.json(), list) else []
        for s in sprints:
            c.delete(f"{SPRINTS_URL}/{s['id']}")
        print(f"  Sprints deleted: {len(sprints)}")

    # — Test cases —
    r = c.get(TESTCASES_URL, params={"project_id": pid, "limit": 500})
    tcs = r.json() if r.ok else []
    tcs = tcs if isinstance(tcs, list) else tcs.get("items", [])
    for t in tcs:
        c.delete(f"{TESTCASES_URL}/{t['id']}")
    print(f"  TestCases deleted: {len(tcs)}")

    # — TC Folders (рекурсивно листья → корень) —
    def del_tc_folder(f):
        for ch in f.get("children", []):
            del_tc_folder(ch)
        c.delete(f"{TC_FOLDERS_URL}/{f['id']}")

    r = c.get(TC_FOLDERS_URL, params={"project_id": pid})
    if r.ok:
        data = r.json()
        folders = data.get("folders", data) if isinstance(data, dict) else data
        for f in (folders if isinstance(folders, list) else []):
            del_tc_folder(f)
        print(f"  TC Folders deleted")

    # — Articles —
    r = c.get(ARTICLES_URL, params={"project_id": pid, "limit": 500})
    arts = r.json() if r.ok else []
    arts = arts if isinstance(arts, list) else arts.get("items", [])
    for a in arts:
        c.delete(f"{ARTICLES_URL}/{a['id']}")
    print(f"  Articles deleted: {len(arts)}")

    # — Article Folders —
    def del_art_folder(f):
        for ch in f.get("children", []):
            del_art_folder(ch)
        c.delete(f"{ART_FOLDERS_URL}/{f['id']}")

    r = c.get(ART_FOLDERS_URL, params={"project_id": pid})
    if r.ok:
        data = r.json()
        folders = data.get("folders", data) if isinstance(data, dict) else data
        for f in (folders if isinstance(folders, list) else []):
            del_art_folder(f)
        print(f"  Article Folders deleted")

    # — Test Plans —
    r = c.get(TEST_PLANS_URL, params={"project_id": pid})
    if r.ok:
        tps = r.json()
        tps = tps if isinstance(tps, list) else tps.get("items", [])
        for tp in tps:
            c.delete(f"{TEST_PLANS_URL}/{tp['id']}")
        print(f"  Test Plans deleted: {len(tps)}")

    # — Pechkin Collections —
    r = c.get(f"{PECHKIN_URL}/collections", params={"project_id": pid})
    if r.ok:
        cols = r.json() if isinstance(r.json(), list) else []
        for col in cols:
            c.delete(f"{PECHKIN_URL}/collections/{col['id']}")
        print(f"  Pechkin collections deleted: {len(cols)}")

    print("  [DONE] Cleanup complete\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — TASK TYPES
# ════════════════════════════════════════════════════════════════════════════

def load_types():
    print("[1] Loading task types...")
    r = c.get(f"{SETTINGS_URL}/types", params={"project_id": PROJECT_ID})
    if r.ok:
        for t in r.json():
            TYPES[t["slug"]] = t["id"]
    print(f"  Types: {list(TYPES.keys())}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — COMPONENTS (5)
# ════════════════════════════════════════════════════════════════════════════

COMPONENTS_DEF = [
    ("Authentication",      "JWT, refresh-токены, multi-tenancy, управление пользователями"),
    ("Issues & Sprints",    "Kanban-доска, JQL-фильтрация, бэклог, спринты, дашборд"),
    ("Articles",            "GridEditor, breadcrumbs, TOC, история версий, PDF-экспорт"),
    ("QA Module",           "Тест-кейсы, тест-планы, прогоны, матрица, QA-дашборд"),
    ("Generator & Pechkin", "Static/LLM/EVA-генераторы, HTTP-клиент Pechkin"),
]

def create_components():
    print("[2] Components...")
    for name, desc in COMPONENTS_DEF:
        r = c.post(COMPONENTS_URL, json={"name": name, "description": desc, "project_id": PROJECT_ID})
        d = ok(r, name)
        if d:
            COMPONENTS[name] = d.get("id", "")
    print(f"  Created: {len(COMPONENTS)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — EPICS (6)
# ════════════════════════════════════════════════════════════════════════════

EPICS_DEF = [
    ("EP-AUTH",    "Аутентификация и безопасность",
     "JWT-авторизация, refresh-токены, multi-tenancy и управление пользователями. "
     "Основа всей системы — без надёжной авторизации все остальные модули недоступны.",
     "Authentication"),
    ("EP-ISSUES",  "Issues и Sprint Management",
     "Полноценный трекер задач в стиле Jira: Kanban-доска, JQL-фильтрация, "
     "бэклог с ранжированием, спринты с burndown, дашборд метрик.",
     "Issues & Sprints"),
    ("EP-ARTICLES","База знаний (Articles)",
     "Confluence-подобная база знаний: иерархия папок, блочный редактор GridEditor, "
     "breadcrumbs, TOC, история версий, PDF-экспорт, импорт из .md/.docx.",
     "Articles"),
    ("EP-QA",      "QA: Управление тестированием",
     "TMS в стиле TestIT: тест-кейсы с шагами, тест-планы, прогоны, "
     "матрица результатов, дашборд с трендами и покрытием.",
     "QA Module"),
    ("EP-GEN",     "Генератор тестов (Static / LLM / EVA)",
     "Автоматическая генерация тест-кейсов из OpenAPI-спецификации. "
     "Static (без LLM), LLM (Groq API), EVA — оценка качества тестов.",
     "Generator & Pechkin"),
    ("EP-PECHKIN", "Pechkin HTTP Client",
     "Встроенный HTTP-клиент в стиле Postman: коллекции, переменные окружения, "
     "auth-типы, Collection Runner, история, импорт Postman JSON.",
     "Generator & Pechkin"),
]

def create_epics():
    print("[3] Epics...")
    for key, title, desc, comp in EPICS_DEF:
        r = c.post(TASKS_URL, json={
            "title": title, "description": desc,
            "type_id": TYPES.get("epic"),
            "priority": "high", "status": "done",
            "project_id": PROJECT_ID,
            "component_id": COMPONENTS.get(comp),
            "labels": [key.lower()],
        })
        d = ok(r, f"epic {key}")
        if d: EPICS[key] = d.get("id", "")
    print(f"  Created: {len(EPICS)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — STORIES (18)
# ════════════════════════════════════════════════════════════════════════════

STORIES_DEF = [
    # AUTH
    ("ST-AUTH-1", "JWT Login и Token Refresh",
     "Пользователь входит через username/password → access_token (15 мин) + refresh_token (7 дней). "
     "При 401 — автоматический silent refresh через axios interceptor без перезагрузки страницы.",
     "EP-AUTH", "Authentication", "high"),
    ("ST-AUTH-2", "Мультитенантность и изоляция проектов",
     "Данные изолированы по project_id. check_project_access проверяет права на каждый запрос. "
     "Пользователь видит только свой проект.",
     "EP-AUTH", "Authentication", "high"),
    ("ST-AUTH-3", "Панель администратора",
     "Admin управляет пользователями: создание, смена пароля, деактивация. "
     "Доступно через /settings → Admin tab.",
     "EP-AUTH", "Authentication", "medium"),

    # ISSUES
    ("ST-ISS-1", "Kanban Board и JQL-фильтрация",
     "4 колонки (Todo/In Progress/Review/Done), drag-and-drop карточек, фильтрация по типу. "
     "JQL строка: status = 'todo', priority = high, assignee = currentUser(). "
     "Переключение Board ↔ List view.",
     "EP-ISSUES", "Issues & Sprints", "high"),
    ("ST-ISS-2", "Backlog и Sprint Management",
     "Бэклог — список без спринта, сортировка по rank. Drag-and-drop ранжирования. "
     "Создание спринта, запуск (POST /start), завершение (POST /complete с переносом незакрытых). "
     "Burndown chart и velocity по последним 5 спринтам.",
     "EP-ISSUES", "Issues & Sprints", "high"),
    ("ST-ISS-3", "Детальная карточка Issue",
     "Fullscreen просмотр и редактирование: 3 вкладки (Details/Activity/WorkLog). "
     "Sidebar: Priority, Severity, Component, StoryPoints, Sprint, Assignee, Due Date, Labels. "
     "Вложения через MinIO, логирование времени, custom fields.",
     "EP-ISSUES", "Issues & Sprints", "high"),

    # ARTICLES
    ("ST-ART-1", "GridEditor и полноэкранный редактор",
     "Блочный редактор grid-1: текст, заголовки, списки, callout-блоки (info/warning/note/success), "
     "expand-блоки, код с подсветкой highlight.js. Autosave каждые 60 секунд для существующих статей.",
     "EP-ARTICLES", "Articles", "high"),
    ("ST-ART-2", "ArticleViewer — просмотрщик",
     "Fullscreen просмотр: breadcrumbs (путь от корня), TOC из H1-H3 с IntersectionObserver, "
     "metadata (автор, дата, просмотры), блок дочерних страниц в той же папке.",
     "EP-ARTICLES", "Articles", "medium"),
    ("ST-ART-3", "PDF-экспорт и история версий",
     "PDF через weasyprint: заголовок, breadcrumbs, дата, весь контент включая callout-маркеры. "
     "История версий: список снапшотов, просмотр предыдущей версии в read-only GridEditor.",
     "EP-ARTICLES", "Articles", "medium"),

    # QA
    ("ST-QA-1", "Управление тест-кейсами",
     "Создание кейсов с шагами action/expected/data (StepsEditor). "
     "Иерархия папок max 3 уровня. Bulk-операции. Привязка к Issues. Экспорт CSV.",
     "EP-QA", "QA Module", "high"),
    ("ST-QA-2", "Тест-планы и прогоны",
     "Создание плана, добавление кейсов, запуск прогона. Результаты: passed/failed/blocked/skipped. "
     "Назначение исполнителя на кейс в прогоне. Finish Run фиксирует итоги.",
     "EP-QA", "QA Module", "high"),
    ("ST-QA-3", "QA-дашборд и покрытие",
     "Trend passed/failed по последним 10 прогонам (Chart.js Line). "
     "Distribution по статусам (Pie). Coverage по папкам (Bar). "
     "Топ-5 нестабильных кейсов. Кэш Redis TTL 300s, X-Cache header.",
     "EP-QA", "QA Module", "medium"),

    # GENERATOR
    ("ST-GEN-1", "Static генератор из OpenAPI",
     "Парсинг OpenAPI YAML/JSON: эндпоинты, методы, схемы. "
     "Генерация: happy path + negative + boundary cases. "
     "Форматы: pytest / JavaScript / Postman Collection.",
     "EP-GEN", "Generator & Pechkin", "medium"),
    ("ST-GEN-2", "LLM и EVA анализаторы",
     "LLM-генератор через Groq API для умной генерации с пониманием контекста. "
     "EVA анализирует качество существующих тестов: coverage score, дубликаты, пропущенные edge cases.",
     "EP-GEN", "Generator & Pechkin", "low"),

    # PECHKIN
    ("ST-PECK-1", "Коллекции и управление запросами",
     "Создание коллекций/папок/запросов. Импорт Postman Collection v2.1. "
     "Дерево с контекстным меню (rename/delete/duplicate). Хранение в PostgreSQL.",
     "EP-PECHKIN", "Generator & Pechkin", "high"),
    ("ST-PECK-2", "HTTP-прокси: методы, auth, body",
     "GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS. Auth: Bearer, Basic, API Key. "
     "Body: raw JSON, form-data, x-www-form-urlencoded. "
     "Tabs: Params / Headers / Body / Auth / Pre-request / Tests / Code.",
     "EP-PECHKIN", "Generator & Pechkin", "high"),
    ("ST-PECK-3", "Variables, Collection Runner, History",
     "Переменные scope: global/collection/custom. Подстановка {{varName}} в URL/headers. "
     "Collection Runner: последовательное выполнение, delay, stop_on_error, iterations. "
     "История запросов: status_code, duration, response body.",
     "EP-PECHKIN", "Generator & Pechkin", "medium"),
]

def create_stories():
    print("[4] Stories...")
    for key, title, desc, epic_key, comp, priority in STORIES_DEF:
        r = c.post(TASKS_URL, json={
            "title": title, "description": desc,
            "type_id": TYPES.get("story"),
            "priority": priority, "status": "done",
            "project_id": PROJECT_ID,
            "parent_id": EPICS.get(epic_key),
            "component_id": COMPONENTS.get(comp),
            "labels": [key.lower().replace("-", "_")],
        })
        d = ok(r, f"story {key}")
        if d: STORIES[key] = d.get("id", "")
    print(f"  Created: {len(STORIES)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 5 — BUGS (15) — реальные баги из EL066-069
# ════════════════════════════════════════════════════════════════════════════

BUGS_DEF = [
    # ── EL066 — Pechkin ──────────────────────────────────────────────────
    ("BUG-PECK-001", "Method selector не обновляет v-model",
     "Кастомный CSS-dropdown для выбора HTTP метода не вызывает нативный change event "
     "на <select v-model=\"req.method\">. Визуально POST выбран, но req.method = 'GET'. "
     "Все запросы отправляются как GET независимо от выбора.",
     "critical", "ST-PECK-2", "el066"),
    ("BUG-PECK-002", "Variables API PUT → 500 Internal Server Error",
     "PUT /api/v1/pechkin/collections/{id}/variables → 500. "
     "upsert_variable использует INSERT ON CONFLICT без нужного уникального constraint. "
     "Переменные окружения полностью нефункциональны.",
     "critical", "ST-PECK-3", "el066"),
    ("BUG-PECK-003", "Mode switcher кнопки не реагируют на обычный click",
     "Static/LLM/EVA/Pechkin кнопки не переключаются стандартным кликом — "
     "требуется element.click() через JS. Причина: вложенный <span> поглощает события.",
     "critical", "ST-GEN-1", "el066"),
    ("BUG-PECK-004", "form-data сериализация через JSON.stringify",
     "RequestEditor.vue send(): x-www-form-urlencoded тело сериализуется через JSON.stringify(). "
     "Правильно: new URLSearchParams().toString(). "
     "Сервер получает JSON вместо кодированных form-полей.",
     "high", "ST-PECK-2", "el066"),
    ("BUG-PECK-005", "syncParamsToUrl ломается при URL с {{varName}}",
     "new URL('{{baseUrl}}/api') → TypeError. Params не синхронизируются с URL "
     "когда URL содержит переменные. catch блок молча проглатывает ошибку.",
     "high", "ST-PECK-3", "el066"),
    # ── EL067 — Pechkin Fixes ────────────────────────────────────────────
    ("BUG-PECK-006", "History: status_code показывает 0 вместо реального",
     "После 200 GET запроса вкладка History показывает статус '0'. "
     "history_to_dict неправильно маппит поле status_code из модели.",
     "medium", "ST-PECK-3", "el067"),
    # ── EL068 — Issues ───────────────────────────────────────────────────
    ("BUG-ISS-001", "JQL GET /tasks?jql=... → 500 Internal Server Error",
     "JQL компилятор падает с неперехваченным исключением на валидных запросах. "
     "Нет broad exception handler вокруг list_tasks_jql(). "
     "Вся JQL-фильтрация недоступна.",
     "critical", "ST-ISS-1", "el068"),
    ("BUG-ISS-002", "Sprints 404 — нет эндпоинтов start и complete",
     "POST /api/v1/sprints/{id}/start и POST /api/v1/sprints/{id}/complete → 404. "
     "Роутер зарегистрирован в main.py, но эти два хэндлера не реализованы. "
     "Весь модуль спринтов недоступен из UI.",
     "high", "ST-ISS-2", "el068"),
    ("BUG-ISS-003", "POST /tasks без project_id → 500",
     "TaskCreate.project_id опциональный, но при None → IntegrityError в БД. "
     "Нет fallback на default_project (в отличие от /articles). "
     "58 Cypress тестов каскадно упали из-за этого бага.",
     "high", "ST-ISS-1", "el068"),
    ("BUG-ISS-004", "Work-logs API 404 — неверный путь в тестах",
     "Тесты вызывали /tasks/{id}/work-logs. "
     "Реальный путь: POST /api/v1/work-logs (с issue_id в теле), "
     "GET /api/v1/work-logs/issues/{id}.",
     "high", "ST-ISS-3", "el068"),
    # ── EL068 — Articles ─────────────────────────────────────────────────
    ("BUG-ART-001", "PDF export → 500 Internal Server Error",
     "weasyprint.HTML(string=html).write_pdf() падает без try/except. "
     "Нет проверки ImportError для weasyprint. "
     "Кнопка PDF в ArticleViewer не работает.",
     "critical", "ST-ART-3", "el068"),
    ("BUG-ART-002", "DOCX import → 500",
     "python-docx exception не перехватывается при импорте .docx файла. "
     "Весь endpoint падает с 500 вместо warnings + graceful fallback.",
     "medium", "ST-ART-1", "el068"),
    ("BUG-ART-003", "FolderTree context menu: .context-menu vs .ctx-menu",
     "Cypress тесты искали .context-menu, реальный класс — .ctx-menu. "
     "Right-click на папке в части окружений не показывает меню rename/delete.",
     "medium", "ST-ART-1", "el068"),
    ("BUG-ISS-005", "Dashboard stats: top_assignees vs by_assignee",
     "GET /tasks/dashboard/stats возвращает ключ 'by_assignee', "
     "тесты и документация ожидают 'top_assignees'. "
     "Несоответствие имён полей.",
     "medium", "ST-ISS-1", "el068"),
    # ── EL066 LOW ────────────────────────────────────────────────────────
    ("BUG-PECK-007", "collectAllRequests не рекурсивный для 3+ уровней",
     "CollectionTree.vue collectAllRequests() обходит folders[].children[], "
     "но не folders[].children[].children[]. "
     "Запросы из 3-го уровня вложенности не попадают в Collection Runner.",
     "low", "ST-PECK-1", "el066"),
]

def create_bugs():
    print("[5] Bugs...")
    for key, title, desc, severity, story_key, sprint_label in BUGS_DEF:
        priority = "high" if severity in ("critical", "high") else "medium"
        r = c.post(TASKS_URL, json={
            "title": title, "description": desc,
            "type_id": TYPES.get("bug"),
            "priority": priority, "severity": severity,
            "status": "done",
            "project_id": PROJECT_ID,
            "parent_id": STORIES.get(story_key),
            "component_id": COMPONENTS.get(
                {"ST-PECK-1": "Generator & Pechkin",
                 "ST-PECK-2": "Generator & Pechkin",
                 "ST-PECK-3": "Generator & Pechkin",
                 "ST-GEN-1":  "Generator & Pechkin",
                 "ST-ISS-1":  "Issues & Sprints",
                 "ST-ISS-2":  "Issues & Sprints",
                 "ST-ISS-3":  "Issues & Sprints",
                 "ST-ART-1":  "Articles",
                 "ST-ART-3":  "Articles"}.get(story_key, "")
            ),
            "labels": [key.lower().replace("-", "_"), sprint_label],
        })
        d = ok(r, f"bug {key}")
        if d: BUGS[key] = d.get("id", "")
    print(f"  Created: {len(BUGS)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SPRINTS (4)
# ════════════════════════════════════════════════════════════════════════════

SPRINTS_DEF = [
    ("EL-QA-1: Pechkin Audit",
     "Полный QA-аудит Pechkin HTTP Client. 181 тест, pass rate 40%, 12 багов.",
     "2026-02-01", "2026-02-14", "completed"),
    ("EL-FIX-1: Pechkin Fixes",
     "Исправление 12 багов: method selector, variables API 500, mode switcher click.",
     "2026-02-15", "2026-02-28", "completed"),
    ("EL-QA-2: Issues & Articles Audit",
     "QA Issues и Articles. 325 тестов, pass rate 64.5%, 15 багов.",
     "2026-03-01", "2026-03-14", "completed"),
    ("EL-FIX-2: Issues & Articles Fixes",
     "JQL exception handler, Sprints start/complete, PDF try/except, POST tasks fallback.",
     "2026-03-15", "2026-03-28", "active"),
]

def create_sprints():
    print("[6] Sprints...")
    for name, goal, start, end, status in SPRINTS_DEF:
        r = c.post(SPRINTS_URL, json={
            "name": name, "goal": goal,
            "start_date": start, "end_date": end,
            "project_id": PROJECT_ID,
        })
        d = ok(r, f"sprint {name[:20]}")
        if not d:
            continue
        sid = d.get("id", "")
        label = name[:8]
        SPRINTS[label] = sid

        if status in ("active", "completed"):
            sr = c.post(f"{SPRINTS_URL}/{sid}/start")
            if not sr.ok:
                print(f"    [WARN] start sprint {name[:20]}: {sr.status_code} {sr.text[:80]}")
        if status == "completed":
            cr = c.post(f"{SPRINTS_URL}/{sid}/complete", json={})
            if not cr.ok:
                print(f"    [WARN] complete sprint: {cr.status_code} {cr.text[:80]}")

    print(f"  Created: {len(SPRINTS)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 7 — TC FOLDERS
# ════════════════════════════════════════════════════════════════════════════

TC_STRUCTURE = {
    "Authentication":   ["Login & Auth Guard", "JWT Refresh"],
    "Issues":           ["Board & Kanban", "Backlog & Sprints", "Issue Detail & Sidebar", "Dashboard"],
    "Articles":         ["Editor & GridEditor", "Viewer & Navigation", "Folder Management"],
    "QA Module":        ["Test Cases CRUD", "Test Plans & Runs", "QA Dashboard"],
    "Generator":        ["Static Generator", "Pechkin HTTP Client", "LLM & EVA"],
    "API Tests":        ["Issues API", "Articles API", "Pechkin API"],
}

def create_tc_folders():
    print("[7] TC Folders...")
    pid = PROJECT_ID
    for parent_name, children in TC_STRUCTURE.items():
        r = c.post(TC_FOLDERS_URL, json={"name": parent_name, "project_id": pid})
        d = ok(r, f"tcf {parent_name}")
        if not d:
            continue
        TC_FOLDERS[parent_name] = d.get("id", "")
        for child in children:
            r2 = c.post(TC_FOLDERS_URL, json={
                "name": child,
                "parent_id": TC_FOLDERS[parent_name],
                "project_id": pid,
            })
            d2 = ok(r2, f"tcf {child}")
            if d2:
                TC_FOLDERS[child] = d2.get("id", "")
    print(f"  Created: {len(TC_FOLDERS)} folders\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 8 — TEST CASES (45)
# ════════════════════════════════════════════════════════════════════════════

def steps(*rows):
    return [{"action": a, "expected": e, "data": d or ""} for a, e, d in rows]


TC_DATA = [
    # ── Authentication ────────────────────────────────────────────────────
    ("TC-AUTH-01", "Успешный вход (Login)", "Login & Auth Guard", "critical",
     steps(
         ("POST /auth/login {username, password}", "HTTP 200, access_token + refresh_token в теле", None),
         ("Сохранить access_token в localStorage", "Токен сохранён", None),
         ("Перейти на /dashboard/#/issues", "Страница Issues загружена, токен в headers", None),
     )),
    ("TC-AUTH-02", "Неверные credentials → 401", "Login & Auth Guard", "high",
     steps(
         ("POST /auth/login {username: 'owner1', password: 'wrong'}", "HTTP 401, тело: {detail: 'Invalid credentials'}", None),
         ("Проверить UI", "Сообщение об ошибке видно. URL остаётся /login. Токен НЕ сохранён", None),
     )),
    ("TC-AUTH-03", "Auth Guard: редирект без токена", "Login & Auth Guard", "high",
     steps(
         ("Удалить access_token из localStorage", "localStorage['access_token'] = null", None),
         ("Перейти на /dashboard/#/issues", "Vue Router выполняет навигацию", None),
         ("Наблюдать URL", "Редирект на /#/login. Страница Issues НЕ показана", None),
     )),
    ("TC-AUTH-04", "Silent JWT Refresh при 401", "JWT Refresh", "medium",
     steps(
         ("Установить истёкший access_token", "Токен с exp в прошлом в localStorage", None),
         ("Открыть любой API запрос через UI (Issues)", "Запрос уходит с истёкшим токеном → 401", None),
         ("Axios interceptor делает POST /auth/refresh", "Новый токен получен и сохранён", None),
         ("Исходный запрос повторяется с новым токеном", "Страница загрузилась без перехода на /login", None),
     )),

    # ── Board & Kanban ────────────────────────────────────────────────────
    ("TC-ISS-01", "Kanban: 4 колонки и карточки", "Board & Kanban", "critical",
     steps(
         ("Открыть /dashboard/#/issues → вкладка Board", "Видны 4 колонки: To Do / In Progress / Review / Done", None),
         ("Каждая колонка имеет заголовок и счётчик", "column-title + column-count видны", None),
         ("Карточка содержит", "Полоса приоритета, human_id (EL-N), title, assignee, severity badge", None),
         ("Overdue задача", "Due date подсвечена красным (.due-date.overdue)", None),
     )),
    ("TC-ISS-02", "Kanban: Drag-and-Drop между колонками", "Board & Kanban", "high",
     steps(
         ("Создать задачу в To Do", "EL-N виден в колонке To Do", None),
         ("Перетащить карточку в In Progress", "dragstart → dragover → drop", None),
         ("Проверить API", "PUT /tasks/{id} {status: 'in_progress'} → 200", None),
         ("Карточка в In Progress, счётчики обновлены", "To Do: -1, In Progress: +1", None),
     )),
    ("TC-ISS-03", "JQL фильтрация: валидный запрос → 200 (не 500)", "Board & Kanban", "critical",
     steps(
         ("Ввести в JQL Bar: status = 'todo'", "Текст введён", "status = \"todo\""),
         ("Enter / Apply", "GET /tasks?jql=status='todo' → 200 (критично: не 500!)", None),
         ("Режим List включился", "Только todo задачи в списке", None),
     )),
    ("TC-ISS-04", "JQL невалидный синтаксис → 400 с сообщением", "Board & Kanban", "high",
     steps(
         ("Ввести: abc %%% xyz", "Текст введён", "abc %%% xyz"),
         ("Enter", "GET /tasks?jql=abc+%%%+xyz → 400 (не 500!)", None),
         ("UI показывает сообщение об ошибке", "Приложение не крашнулось", None),
     )),

    # ── Backlog & Sprints ────────────────────────────────────────────────
    ("TC-ISS-05", "Backlog: список и ранжирование", "Backlog & Sprints", "high",
     steps(
         ("Открыть вкладку Backlog", "BacklogView загружен, список задач без спринта", None),
         ("Drag-and-drop задачу", "PATCH /tasks/{id}/rank → 200. Список перерисован без перезагрузки", None),
     )),
    ("TC-ISS-06", "Sprint: полный жизненный цикл", "Backlog & Sprints", "critical",
     steps(
         ("Нажать + Create Sprint", "Форма: Name, Goal, Start Date, End Date", None),
         ("Заполнить и Submit", "POST /api/v1/sprints → 201. Sprint Panel видна", None),
         ("Start Sprint", "POST /api/v1/sprints/{id}/start → 200. status = active", None),
         ("Второй Start в том же проекте", "→ 409 Conflict (один активный спринт)", None),
         ("Complete Sprint", "POST /api/v1/sprints/{id}/complete → 200. Незакрытые → backlog", None),
         ("Velocity chart", "GET /api/v1/sprints/velocity → данные обновились", None),
     )),

    # ── Issue Detail & Sidebar ───────────────────────────────────────────
    ("TC-ISS-07", "Создание Issue через модальное окно", "Issue Detail & Sidebar", "critical",
     steps(
         ("Нажать + New Issue", "Модальное окно с полями: Title*, Type, Priority, Severity, Environment, Assignee, Due Date, Labels", None),
         ("Попытка без Title", "Submit не выполняется (required validation)", None),
         ("Заполнить все поля, Create", "POST /tasks → 200. human_id = EL-N. Задача в To Do", None),
     )),
    ("TC-ISS-08", "IssueDetailView: редактирование и сохранение", "Issue Detail & Sidebar", "high",
     steps(
         ("Кликнуть карточку → TaskViewer → Edit", "IssueDetailView открылся fullscreen", None),
         ("Изменить Title, Priority=High, Story Points=5", "Поля в edit mode", None),
         ("Save", "PUT /tasks/{id} → 200. Изменения персистентны при повторном открытии", None),
         ("Cancel", "Форма вернулась к исходным данным без сохранения", None),
     )),
    ("TC-ISS-09", "Sidebar: Component, Sprint, Custom Fields", "Issue Detail & Sidebar", "medium",
     steps(
         ("Edit mode → выбрать Component из dropdown", "PUT /tasks/{id} с component_id", None),
         ("Sidebar показывает Sprint badge если задача в спринте", "Sprint: EL-QA-1 badge виден", None),
         ("Custom Fields секция видна если есть поля проекта", "Поля отображаются и редактируются", None),
     )),
    ("TC-ISS-10", "WorkLog: логирование времени", "Issue Detail & Sidebar", "medium",
     steps(
         ("Открыть вкладку Work Log", "WorkLogBlock: прогресс-бар estimated/spent, кнопка Log Work", None),
         ("Log Work: 2.5 часа, comment", "POST /api/v1/work-logs → 201", None),
         ("spent_hours обновился", "Прогресс-бар пересчитан", None),
     )),

    # ── Dashboard ────────────────────────────────────────────────────────
    ("TC-ISS-11", "Dashboard: stats и Redis кэш", "Dashboard", "high",
     steps(
         ("Открыть вкладку Dashboard", "GET /tasks/dashboard/stats?project_id=... → 200", None),
         ("Первый запрос", "X-Cache: MISS в response headers", None),
         ("Повторный запрос (refresh)", "X-Cache: HIT — данные из Redis", None),
         ("Чарты видны", "by_type, by_priority отображены. Нет краша", None),
     )),

    # ── Editor & GridEditor ──────────────────────────────────────────────
    ("TC-ART-01", "Создание статьи: fullscreen editor", "Editor & GridEditor", "critical",
     steps(
         ("+ New Article", "Fullscreen editor открылся (.editor-fullscreen)", None),
         ("Ввести title, нажать ▼ Meta", "Subheader: Category, Tags поля видны", None),
         ("Добавить контент в GridEditor", "Блоки добавляются в grid-1 структуру", None),
         ("Save", "POST /articles → 200. Slug присвоен. Статья в списке со статусом draft", None),
     )),
    ("TC-ART-02", "Autosave при редактировании", "Editor & GridEditor", "medium",
     steps(
         ("Открыть существующую статью → Edit", "Editor с данными статьи", None),
         ("Изменить контент (isDirty = true)", "Изменения не сохранены", None),
         ("Ждать 60 секунд", "Статус 'Сохранение...' → PUT /articles/{id} → 200 → '✓ Сохранено HH:MM'", None),
     )),
    ("TC-ART-03", "Import .md файла", "Editor & GridEditor", "medium",
     steps(
         ("Кнопка Import в списке статей", "file input (accept='.md,.docx') активирован", None),
         ("Выбрать .md файл < 5MB", "POST /articles/import → 200", None),
         ("Alert 'Article imported: ...'", "Статья в списке, title из H1 файла", None),
     )),
    ("TC-ART-04", "Import: файл > 5MB → валидация", "Editor & GridEditor", "low",
     steps(
         ("Выбрать файл > 5MB для импорта", "validateFile() выполняется", None),
         ("Alert 'File too large. Max: 5 MB'", "Файл НЕ импортирован, запрос НЕ отправлен", None),
     )),

    # ── Viewer & Navigation ──────────────────────────────────────────────
    ("TC-ART-05", "ArticleViewer: breadcrumbs и metadata", "Viewer & Navigation", "high",
     steps(
         ("Создать статью в папке Level1/Level2, открыть", "ArticleViewer fullscreen", None),
         ("Breadcrumbs", "Показаны: Articles › Level1 › Level2 › Название статьи", None),
         ("Кликнуть Level1 в breadcrumbs", "emit navigate-to-folder → папка Level1 выбрана в sidebar", None),
         ("Meta строка", "Автор, дата обновления, N просмотров", None),
     )),
    ("TC-ART-06", "TOC: автогенерация и IntersectionObserver", "Viewer & Navigation", "medium",
     steps(
         ("Открыть статью с H1/H2/H3 при ширине ≥ 1280px", "TOC справа (.viewer-toc) видна", None),
         ("TOC items соответствуют заголовкам", "Каждый H1-H3 — пункт TOC", None),
         ("Кликнуть пункт TOC", "Smooth scroll к заголовку", None),
         ("Прокрутить к H2 разделу", "Соответствующий TOC пункт подсвечен (class active)", None),
         ("Окно < 1280px", "TOC скрыта, контент 100% ширины", None),
     )),
    ("TC-ART-07", "PDF Export → не 500", "Viewer & Navigation", "critical",
     steps(
         ("Открыть статью в ArticleViewer", "Кнопка PDF в topbar", None),
         ("Нажать PDF", "GET /articles/{id}/export/pdf → 200 (не 500!) или 501 (weasyprint не установлен)", None),
         ("При 200", "Content-Type: application/pdf. Файл скачивается", None),
         ("При 501", "Понятное сообщение. НЕ 500 Internal Server Error", None),
     )),
    ("TC-ART-08", "История версий: список и preview", "Viewer & Navigation", "medium",
     steps(
         ("Сохранить статью 3 раза через PUT", "3 версии в article_versions таблице", None),
         ("Нажать История в topbar", "Sliding panel открылась. GET /articles/{id}/versions → 3 items", None),
         ("Кликнуть на версию 1", "GET /articles/{id}/versions/{v1} → content snapshot", None),
         ("Version preview", "GridEditor readonly с содержимым версии 1", None),
         ("Кнопка ✕", "Panel закрылась (transform: translateX(100%))", None),
     )),

    # ── Folder Management ────────────────────────────────────────────────
    ("TC-ART-09", "FolderTree CRUD", "Folder Management", "high",
     steps(
         ("Создать папку через + в FolderTree", "POST /articles/folders → id возвращён", None),
         ("Right-click → Rename (.ctx-menu)", ".ctx-menu .ctx-item visible. Rename выполнен → PUT /articles/folders/{id}", None),
         ("Right-click → Delete, подтвердить", "DELETE /articles/folders/{id} → 200. Папка исчезла из дерева", None),
     )),
    ("TC-ART-10", "Drag-and-drop статьи в папку", "Folder Management", "medium",
     steps(
         ("Drag на .article-row (draggable=true)", "dataTransfer: {type: 'article', id: '...'}", None),
         ("Drop на папку в FolderTree", "POST /articles/{id}/move-to-folder → 200", None),
         ("Кликнуть папку в sidebar", "Статья теперь в этой папке", None),
     )),

    # ── Test Cases CRUD ──────────────────────────────────────────────────
    ("TC-QA-01", "Создание тест-кейса с шагами", "Test Cases CRUD", "critical",
     steps(
         ("QA → Tree → + New Test Case", "Форма создания открылась", None),
         ("StepsEditor: + Step", "Новая строка: #, Action, Expected, Data", None),
         ("Заполнить 3 шага, Tab в последней ячейке → новая строка", "4-я строка добавлена", None),
         ("Save", "POST /testcases → 200. steps: [{action, expected, data}, ...]", None),
     )),
    ("TC-QA-02", "Bulk-операции над тест-кейсами", "Test Cases CRUD", "high",
     steps(
         ("Выбрать 3 кейса через checkbox", "Toolbar bulk-операций появился", None),
         ("Add to Plan → выбрать план", "3 кейса добавлены. counter плана обновился", None),
     )),

    # ── Test Plans & Runs ────────────────────────────────────────────────
    ("TC-QA-03", "Тест-план: создание и запуск прогона", "Test Plans & Runs", "critical",
     steps(
         ("QA → Test Plans → + New Plan", "POST /v1/test-plans → план создан", None),
         ("Добавить 5 кейсов в план", "POST /v1/test-plans/{id}/cases", None),
         ("Start Run", "Прогон создан. Экран выполнения открылся", None),
         ("Отметить passed/failed/blocked, Finish Run", "POST /v1/test-plans/runs/{id}/finish → 200", None),
     )),
    ("TC-QA-04", "RunsMatrix: матрица результатов", "Test Plans & Runs", "high",
     steps(
         ("Провести 3 прогона с разными результатами", "3 прогона в истории плана", None),
         ("Открыть детальный вид плана", "RunsMatrix видна под списком кейсов", None),
         ("Строки = кейсы, столбцы = прогоны", "Ячейки: зелёный/красный/серый/оранжевый", None),
     )),

    # ── QA Dashboard ────────────────────────────────────────────────────
    ("TC-QA-05", "QA Dashboard: trend, coverage, кэш", "QA Dashboard", "medium",
     steps(
         ("QA → Dashboard после нескольких прогонов", "GET /api/v1/qa/dashboard → 200", None),
         ("Trend chart (Chart.js Line)", "X=прогоны, Y=% passed. Минимум 1 точка", None),
         ("Coverage bar chart", "Процент покрытия по папкам тест-кейсов", None),
         ("Повторный запрос", "X-Cache: HIT (Redis TTL 300s)", None),
     )),

    # ── Static Generator ────────────────────────────────────────────────
    ("TC-GEN-01", "Static генератор: парсинг OpenAPI", "Static Generator", "high",
     steps(
         ("Generator → Static → вставить OpenAPI YAML", "Спецификация принята", None),
         ("Endpoint list слева", "Все endpoints распарсены", None),
         ("Выбрать endpoint, проверить код справа", "pytest код с happy path + negative cases", None),
         ("Переключить Framework → JavaScript", "Код в синтаксисе fetch/Jest", None),
     )),
    ("TC-GEN-02", "Static: форматы pytest/JS/Postman", "Static Generator", "medium",
     steps(
         ("pytest", "import pytest + def test_xxx() структура", None),
         ("JavaScript", "async/await + fetch() или axios", None),
         ("Postman", "JSON collection с pm.test() в tests скрипте", None),
     )),

    # ── Pechkin HTTP Client ──────────────────────────────────────────────
    ("TC-PECK-01", "Pechkin: отправка GET запроса", "Pechkin HTTP Client", "critical",
     steps(
         ("Generator → Pechkin → создать запрос", "Редактор с пустым URL", None),
         ("URL: https://httpbin.org/get, метод GET", "select.method-select = GET", None),
         ("Send", "POST /api/v1/pechkin/execute → 200. Response panel: status 200, duration > 0", None),
         ("Body tab: JSON в Pretty режиме", "httpbin ответ отформатирован", None),
     )),
    ("TC-PECK-02", "Pechkin: все HTTP методы", "Pechkin HTTP Client", "high",
     steps(
         ("POST httpbin.org/post + body {test: 1}", "status_code=200", "POST + JSON"),
         ("PUT httpbin.org/put", "200", None),
         ("PATCH httpbin.org/patch", "200", None),
         ("DELETE httpbin.org/delete", "200", None),
         ("HEAD httpbin.org/get", "200, пустое тело", None),
     )),
    ("TC-PECK-03", "Pechkin: Bearer Auth", "Pechkin HTTP Client", "high",
     steps(
         ("Auth вкладка → Bearer Token → ввести test-token-123", "Поле Token заполнено", "test-token-123"),
         ("Send на httpbin.org/get", "В response.headers.Authorization: Bearer test-token-123", None),
     )),
    ("TC-PECK-04", "Pechkin: Variables {{varName}}", "Pechkin HTTP Client", "high",
     steps(
         ("⚙ Variables Panel → добавить baseUrl = https://httpbin.org", "Переменная сохранена через PUT /variables", None),
         ("URL: {{baseUrl}}/get, Send", "URL разрешился. Запрос успешен (200)", None),
     )),
    ("TC-PECK-05", "Pechkin: Code Generation", "Pechkin HTTP Client", "medium",
     steps(
         ("Настроить POST + body + Authorization header", "Конфиг запроса готов", None),
         ("Code tab → cURL", "curl -X POST ... -H 'Authorization: Bearer ...' -d '{...}'", None),
         ("Python", "import requests\\nresp = requests.post(..., json={'key': 'val'})", None),
         ("JavaScript", "const resp = await fetch('...', {method: 'POST', ...})", None),
     )),
    ("TC-PECK-06", "Pechkin: Collection Runner", "Pechkin HTTP Client", "medium",
     steps(
         ("▶ рядом с коллекцией", "Collection Runner modal открылся", None),
         ("Run", "Запросы выполняются последовательно. Прогресс-бар растёт", None),
         ("Результаты", "status_code, duration, passed/failed для каждого", None),
         ("Export CSV", "Файл .csv скачивается с результатами", None),
     )),

    # ── Issues API ──────────────────────────────────────────────────────
    ("TC-API-01", "API: Tasks CRUD полный цикл", "Issues API", "critical",
     steps(
         ("POST /tasks {title, priority, project_id} → 200", "id и human_id в ответе", None),
         ("GET /tasks/{id} → 200", "Поля: attachments, work_logs, custom_field_values присутствуют", None),
         ("PUT /tasks/{id} {title: 'Updated'} → 200", "Изменения в GET /tasks/{id}", None),
         ("DELETE /tasks/{id} → 200", "GET /tasks/{id} → 404", None),
     )),
    ("TC-API-02", "API: Board структура и JQL", "Issues API", "high",
     steps(
         ("GET /tasks/board → 200", "Объект: {todo: [], in_progress: [], review: [], done: []}", None),
         ("GET /tasks/board?type_slug=bug", "Только Bug задачи", None),
         ("GET /tasks?jql=status = 'todo' → не 500", "200 или 400, критично: не 500", None),
         ("GET /tasks?jql=abc %%% xyz → 400", "detail.error = 'jql_syntax_error'", None),
     )),
    ("TC-API-03", "API: Sprints start и complete", "Issues API", "critical",
     steps(
         ("POST /api/v1/sprints {name, project_id} → 201", "Sprint создан с id", None),
         ("POST /api/v1/sprints/{id}/start → 200", "status = active (не 404!)", None),
         ("POST /api/v1/sprints/{id}/start снова → 409", "Нельзя запустить уже активный", None),
         ("POST /api/v1/sprints/{id}/complete → 200", "status = completed", None),
     )),

    # ── Articles API ────────────────────────────────────────────────────
    ("TC-API-04", "API: Articles CRUD", "Articles API", "critical",
     steps(
         ("POST /articles {title, content: grid-1 JSON} → 200", "id и slug в ответе", None),
         ("GET /articles/{id} → 200", "content, status, tags, slug в объекте", None),
         ("PUT /articles/{id} {status: 'published'} → 200", "GET → status = published", None),
         ("DELETE /articles/{id} → 200", "GET /articles/{id} → 404", None),
     )),
    ("TC-API-05", "API: PDF Export → не 500", "Articles API", "critical",
     steps(
         ("GET /articles/{id}/export/pdf → не 500", "Критично: 200 (PDF) или 501 (weasyprint не установлен)", None),
         ("При 200: Content-Type: application/pdf", "Файл валидный", None),
         ("При 501: понятное сообщение", "НЕ 500 Internal Server Error", None),
     )),
    ("TC-API-06", "API: Versions — история изменений", "Articles API", "high",
     steps(
         ("Обновить статью через PUT 3 раза", "3 снапшота в article_versions", None),
         ("GET /articles/{id}/versions → список из 3", "id, title, saved_by, created_at", None),
         ("GET /articles/{id}/versions/{v_id}", "content — полный снапшот статьи", None),
     )),
    ("TC-API-07", "API: Article Folders и Breadcrumbs", "Articles API", "high",
     steps(
         ("POST /articles/folders {name} → 200 или 201", "id в ответе", None),
         ("Создать подпапку с parent_id", "Вложенность в GET /articles/folders", None),
         ("Создать статью в подпапке, GET /articles/{id}/breadcrumbs", "[root, parent, folder, article]", None),
     )),

    # ── Pechkin API ─────────────────────────────────────────────────────
    ("TC-API-08", "API: Pechkin execute все методы", "Pechkin API", "critical",
     steps(
         ("POST /api/v1/pechkin/execute {method: GET, url: httpbin.org/get}", "status_code=200, duration>0, error=null", None),
         ("POST + PUT + PATCH + DELETE + HEAD → все 200", "Все методы проксируются", None),
         ("Невалидный URL", "error в ответе, не 500. HTTP 200 от FastAPI", None),
     )),
    ("TC-API-09", "API: Pechkin Variables upsert → не 500", "Pechkin API", "critical",
     steps(
         ("PUT /api/v1/pechkin/collections/{id}/variables {scope, name, value}", "200 (не 500!)", None),
         ("GET /api/v1/pechkin/collections/{id}/variables", "Переменная в списке", None),
         ("Повторный PUT → upsert (не duplicate)", "Значение обновлено", None),
         ("DELETE /api/v1/pechkin/variables/{id} → 200", "Переменная удалена", None),
     )),
]

def create_testcases():
    print("[8] Test Cases...")
    created = 0
    for tc_id, title, folder_name, priority, tc_steps in TC_DATA:
        folder_id = TC_FOLDERS.get(folder_name)
        if not folder_id:
            print(f"  [WARN] folder not found: '{folder_name}' for {tc_id}")
        r = c.post(TESTCASES_URL, json={
            "title": title,
            "folder_id": folder_id,
            "priority": priority.capitalize(),
            "status": "Ready",
            "automation_status": "automated" if "API" in tc_id else "manual",
            "project_id": PROJECT_ID,
            "steps": tc_steps,
            "tags": [tc_id.lower()],
        })
        d = ok(r, tc_id)
        if d:
            created += 1
        else:
            print(f"  [FAIL] {tc_id}: could not create")
    print(f"  Created: {created}/{len(TC_DATA)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 9 — ARTICLE FOLDERS
# ════════════════════════════════════════════════════════════════════════════

ART_STRUCTURE = {
    "Архитектура":        [],
    "Руководства":        ["Issues и спринты", "База знаний", "QA Module", "Pechkin"],
    "API Reference":      ["Аутентификация", "Tasks API", "Articles API"],
    "QA и тестирование":  [],
}

def create_art_folders():
    print("[9] Article Folders...")
    for parent_name, children in ART_STRUCTURE.items():
        r = c.post(ART_FOLDERS_URL, json={"name": parent_name})
        d = ok(r, f"artf {parent_name}")
        if not d:
            continue
        ART_FOLDERS[parent_name] = d.get("id", "")
        for child_name in children:
            r2 = c.post(ART_FOLDERS_URL, json={
                "name": child_name,
                "parent_id": ART_FOLDERS[parent_name]
            })
            d2 = ok(r2, f"artf {child_name}")
            if d2:
                ART_FOLDERS[child_name] = d2.get("id", "")
    print(f"  Created: {len(ART_FOLDERS)} folders\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 10 — ARTICLES (14)
# ════════════════════════════════════════════════════════════════════════════

ARTICLES_DATA = [
    # ── Архитектура ──────────────────────────────────────────────────────
    ("Архитектура ErrorLens", "Архитектура", "published",
     grid(
         h1("Архитектура ErrorLens"),
         p("ErrorLens — AI-powered QA платформа с многоуровневой архитектурой. "
           "Backend на FastAPI (Python 3.11), frontend на Vue 3, "
           "хранилище — PostgreSQL 16 + Redis + MinIO."),
         h2("Технологический стек"),
         ul("Backend: FastAPI, SQLAlchemy async, Alembic, Pydantic v2",
            "Frontend: Vue 3 Composition API, Pinia, TipTap, Chart.js, Cypress",
            "DB: PostgreSQL 16, PgBouncer (connection pool), Alembic migrations",
            "Cache/Streams: Redis (TTL cache + Event Bus через Streams)",
            "Storage: MinIO S3-compatible для attachments и images",
            "Infra: Docker Compose, Nginx reverse proxy, GitHub Actions CI/CD"),
         h2("Nginx роутинг"),
         p("Nginx слушает :3000. /api/* → backend:8000/ (стрипает /api/ префикс). "
           "Результат: /api/tasks → FastAPI /tasks. "
           "Роуты с /api/v1/ → через nginx: /api/api/v1/sprints."),
         h2("Архитектурный паттерн"),
         ul("Router → Service → Repository → Model (строгое разделение)",
            "HTTPException только в роутерах, бизнес-логика в сервисах",
            "Multi-tenancy: project_id в каждой таблице, check_project_access в middleware"),
         h2("Мониторинг"),
         p("PLG stack: Prometheus :9091, Grafana :3002, Loki :3100. "
           "postgres-exporter и redis-exporter. "
           "Горизонтальное масштабирование при CPU > 70% или p99 > 500ms."),
     )),
    ("JWT Аутентификация", "Архитектура", "published",
     grid(
         h1("JWT Аутентификация и безопасность"),
         p("Двухтокенная схема: access_token (15 мин) + refresh_token (7 дней). "
           "Оба в localStorage. При 401 axios interceptor делает silent refresh."),
         h2("Endpoints"),
         ul("POST /auth/login — получить пару токенов",
            "POST /auth/refresh — обновить access по refresh",
            "GET /auth/me — текущий пользователь",
            "POST /auth/logout — инвалидировать refresh_token"),
         h2("require_auth middleware"),
         code("@router.get('/protected')\nasync def endpoint(user: User = Depends(require_auth)):\n"
              "    # user.id доступен здесь\n    return {'user': user.username}", "python"),
         h2("Multi-tenancy"),
         p("check_project_access(project_id, user, db) проверяет что user является "
           "owner или member проекта. Возвращает 403 если нет доступа."),
     )),
    ("Redis: кэш и Event Bus", "Архитектура", "published",
     grid(
         h1("Redis в ErrorLens"),
         h2("API Cache (TTL 300s)"),
         ul("GET /tasks/dashboard/stats — агрегированная статистика проекта",
            "GET /api/v1/qa/dashboard — QA метрики (trend, coverage)",
            "Ключ: endpoint:project_id. X-Cache: HIT/MISS в response headers"),
         h2("Event Bus (Streams)"),
         p("Publisher не знает о consumers. task.status_changed → stream → "
           "automation workers подписаны и выполняют rules без изменения publisher кода."),
         code("# Публикация\nawait publish(STREAM_TASKS, {\n"
              "    'task_id': task.id,\n    'event': 'status_changed',\n"
              "    'from': old_status, 'to': new_status\n})", "python"),
         h2("PgBouncer"),
         p("errorlens-pgbouncer-1 в transaction mode перед PostgreSQL. "
           "Максимизирует использование connection pool при async SQLAlchemy."),
     )),

    # ── Руководства ──────────────────────────────────────────────────────
    ("Руководство: Issues и Sprint Management", "Issues и спринты", "published",
     grid(
         h1("Issues и Sprint Management"),
         h2("Быстрый старт"),
         ul("+ New Issue → заполнить Title (обязательно), Type, Priority",
            "Kanban: перетащить карточку между колонками для смены статуса",
            "JQL Bar: status = 'todo' AND priority = high для фильтрации",
            "List view: переключить кнопкой 📋 рядом с Type filters"),
         h2("JQL — примеры"),
         code("status = 'in_progress' AND assignee = currentUser()\n"
              "priority IN (high, critical) ORDER BY created DESC\n"
              "due_date < now() AND status != done\n"
              "title ~ 'bug' AND labels = 'el068'", "sql"),
         h2("Спринты"),
         p("Backlog → + Create Sprint → заполнить Name, Goal, даты → Start Sprint. "
           "Drag задачи из backlog в спринт. Complete Sprint переносит незакрытые "
           "задачи в следующий спринт или backlog по выбору."),
         h2("Dashboard"),
         p("Вкладка Dashboard: by_type chart, by_priority chart, top assignees. "
           "Данные кэшируются Redis 300s. X-Cache: HIT/MISS в DevTools Network tab."),
     )),
    ("Руководство: База знаний Articles", "База знаний", "published",
     grid(
         h1("База знаний ErrorLens"),
         h2("Создание статьи"),
         ul("+ New Article → fullscreen editor",
            "Заголовок в поле 'Article title' (крупный input в header)",
            "▼ Meta → Category и Tags (comma-separated)",
            "Контент в GridEditor → Save"),
         h2("GridEditor блоки"),
         ul("Текст с форматированием: Bold, Italic, Inline Code",
            "Заголовки H1-H3 (H2/H3 попадают в TOC автоматически)",
            "Callout: Info (синий), Warning (оранжевый), Note (жёлтый), Success (зелёный)",
            "Expand: раскрываемые секции с заголовком summary",
            "Code block: подсветка через highlight.js, кнопка Copy"),
         h2("Импорт файлов"),
         p("Import в toolbar списка: создаёт новую статью из .md или .docx (max 5MB). "
           "Import from file в subheader редактора: заполняет текущую форму без создания."),
         h2("Просмотрщик"),
         p("Breadcrumbs в шапке, TOC справа (H1-H3, IntersectionObserver), "
           "метаданные (автор, дата, просмотры), блок дочерних статей в папке. "
           "TOC скрывается при ширине < 1280px."),
     )),
    ("Руководство: QA Module", "QA Module", "published",
     grid(
         h1("QA Module — Test Management System"),
         p("QA раздел объединяет тест-кейсы, тест-планы и прогоны в одном интерфейсе. "
           "Вкладки: Tree / Test Plans / Runs / Dashboard."),
         h2("Тест-кейсы"),
         ul("+ New Test Case → StepsEditor (таблица action/expected/data)",
            "Tab в последней ячейке → новая строка шага",
            "Drag строк для изменения порядка",
            "Bulk-операции: чекбокс → Add to Plan / Change Status / Export CSV / Delete"),
         h2("Тест-план и прогон"),
         p("Test Plans → + New Plan → добавить кейсы (bulk drag или кнопка). "
           "Start Run → для каждого кейса: Passed/Failed/Blocked/Skipped + комментарий. "
           "Finish Run фиксирует результаты."),
         h2("Dashboard"),
         p("Trend passed/failed по прогонам (Chart.js). "
           "Coverage по папкам. Кэш Redis TTL 300s."),
     )),
    ("Руководство: Pechkin HTTP Client", "Pechkin", "published",
     grid(
         h1("Pechkin HTTP Client"),
         h2("Коллекции"),
         ul("+ в Collections panel → ввести имя",
            "▶ рядом с коллекцией → Collection Runner",
            "↑ → импорт Postman Collection v2.1 JSON",
            "Right-click на запросе → Duplicate / Delete"),
         h2("Auth типы"),
         ul("Bearer Token: добавляет Authorization: Bearer {token}",
            "Basic Auth: кодирует username:password в base64",
            "API Key: в header или query параметр"),
         h2("Переменные"),
         p("⚙ Variables Panel → добавить {name, value, scope}. "
           "Scope: global (все коллекции), collection (только эта). "
           "Использование: {{varName}} в URL, headers, body."),
         h2("Code Generation"),
         p("Вкладка Code → cURL / Python / JavaScript. Copy в буфер. "
           "Python генерирует корректный dict-литерал для json= параметра."),
     )),

    # ── API Reference ────────────────────────────────────────────────────
    ("API Reference: Аутентификация", "Аутентификация", "published",
     grid(
         h1("Authentication API"),
         h2("POST /auth/login"),
         code('curl -X POST http://192.168.1.74:3000/api/auth/login \\\n'
              '  -H "Content-Type: application/json" \\\n'
              '  -d \'{"username": "admin", "password": "Misha2026"}\'\n\n'
              '# Response 200\n{"access_token": "eyJ...", "refresh_token": "eyJ..."}', "bash"),
         h2("Авторизация запросов"),
         code('curl http://192.168.1.74:3000/api/tasks \\\n'
              '  -H "Authorization: Bearer {access_token}"', "bash"),
         h2("Коды ошибок"),
         ul("401 — неверные credentials или истёкший токен",
            "403 — нет доступа к ресурсу (check_project_access)",
            "422 — отсутствуют обязательные поля"),
     )),
    ("API Reference: Tasks", "Tasks API", "published",
     grid(
         h1("Tasks API Reference"),
         p("Базовый путь (через nginx): /api/tasks"),
         h2("Основные эндпоинты"),
         ul("GET /tasks?project_id=...&jql=...&status=... — список с фильтрами",
            "POST /tasks {title, priority, project_id} → {id, human_id}",
            "GET /tasks/{id} → полный объект с attachments, work_logs, custom_field_values",
            "PUT /tasks/{id} — обновить поля",
            "DELETE /tasks/{id} → 200",
            "GET /tasks/board?project_id=...&type_slug=... → {todo, in_progress, review, done}",
            "GET /tasks/backlog?project_id=... → список без спринта, сортировка по rank",
            "GET /tasks/dashboard/stats?project_id=... → агрегаты, X-Cache header"),
         h2("JQL"),
         code("GET /tasks?jql=status = 'todo' AND priority = high\n"
              "GET /tasks?jql=assignee = currentUser() ORDER BY created DESC", "bash"),
     )),
    ("API Reference: Articles", "Articles API", "published",
     grid(
         h1("Articles API Reference"),
         p("Базовый путь (через nginx): /api/articles"),
         h2("Эндпоинты"),
         ul("GET /articles?project_id=...&status=...&folder_id=... — список",
            "POST /articles {title, content: grid-1 JSON, status} → {id, slug}",
            "PUT /articles/{id} — обновить (создаёт версию в article_versions)",
            "DELETE /articles/{id}",
            "GET /articles/{id}/breadcrumbs → [{id, name, type}]",
            "GET /articles/{id}/export/pdf → PDF blob (или 501 если weasyprint не установлен)",
            "GET /articles/{id}/versions → список снапшотов",
            "GET /articles/{id}/versions/{v_id} → полная версия с content"),
         h2("Формат контента (grid-1)"),
         code('{"version": "grid-1", "rows": [{\n'
              '  "id": "uuid", "columns": [{\n'
              '    "id": "uuid", "span": 12,\n'
              '    "content": {"type": "doc", "content": [...]}\n'
              '  }]\n}]}', "json"),
     )),

    # ── QA и тестирование ────────────────────────────────────────────────
    ("QA Strategy ErrorLens", "QA и тестирование", "published",
     grid(
         h1("QA Strategy ErrorLens"),
         p("Многоуровневое тестирование: unit (pytest), API (pytest+httpx), E2E (Cypress 15.7.1). "
           "Тесты запускаются против живого сервера http://192.168.1.74:3000."),
         h2("Инструменты"),
         ul("pytest + httpx — API тесты в E:\\EL\\QA_Lens\\",
            "Cypress 15.7.1 — E2E в dashboard-vue/cypress/",
            "errorlens-pytest — плагин отправки результатов в Launches",
            "Prometheus + Grafana :3002 — production мониторинг"),
         h2("Паттерн API теста"),
         code("class TestIssuesCRUD:\n"
              "    @pytest.mark.asyncio\n"
              "    async def test_create_returns_id(self, auth_client, project_id):\n"
              "        data = make_task({'project_id': project_id})\n"
              "        resp = await auth_client.post('/api/tasks', json=data)\n"
              "        assert resp.status_code == 200\n"
              "        assert 'id' in resp.json()", "python"),
         h2("Паттерн Cypress теста"),
         code("beforeEach(() => { cy.createIssueViaApi() })\n"
              "afterEach(() => { cy.deleteIssueViaApi('@issueId') })\n"
              "it('kanban has 4 columns', () => {\n"
              "  cy.goToIssues()\n"
              "  cy.get('.kanban-column').should('have.length', 4)\n})", "javascript"),
     )),
    ("EL066-069: История QA итераций", "QA и тестирование", "published",
     grid(
         h1("История QA итераций"),
         h2("EL066 — QA Pechkin (фев 2026)"),
         p("181 тест (113 Cypress + 68 API). Pass rate 40%. 12 багов. "
           "Critical: method selector v-model сломан, variables API 500, mode switcher click."),
         h2("EL067 — Pechkin Fixes"),
         p("Все 12 багов исправлены: нативный <select> вместо кастомного dropdown, "
           "upsert_variable через SELECT+UPDATE/INSERT, pointer-events:none на span подсказку."),
         h2("EL068 — QA Issues & Articles (март 2026)"),
         p("325 тестов. Pass rate 64.5%. 15 багов. "
           "Critical: JQL 500, PDF 500. High: Sprints 404, POST /tasks без project_id → 500."),
         h2("EL069 — Issues & Articles Fixes"),
         p("JQL broad exception handler → 400, добавлены /sprints/{id}/start и complete, "
           "PDF try/except + import check → 501, POST /tasks fallback на default_project. "
           "Тесты: URL mismatches (work-logs, attachments), createIssueViaApi с project_id."),
         h2("Итоги после EL069"),
         ul("API Tests: 86 тестов, ~80%+ pass rate",
            "Cypress E2E: 239 тестов, ~65%+ pass rate",
            "Velocity chart заполнен: 3 завершённых спринта с реальными данными"),
     )),
    ("errorlens-pytest: настройка плагина", "QA и тестирование", "published",
     grid(
         h1("errorlens-pytest — Native Reporting Plugin"),
         p("errorlens-pytest v2.0 — Python пакет для автоматической отправки результатов "
           "в ErrorLens Launches. Поддерживает 12 декораторов и el.step context manager."),
         h2("Установка"),
         code("pip install -e ./errorlens-pytest\n\n"
              "# Конфиг в pyproject.toml\n[tool.errorlens]\nel_url = \"http://192.168.1.74:3000/api\"\n"
              f"el_project_id = \"{PROJECT_ID}\"\nel_launch_name = \"CI Run\"", "bash"),
         h2("Декораторы v2.0"),
         code("import errorlens as el\n\n"
              "@el.feature('Issues')\n@el.story('Kanban Board')\n"
              "@el.severity('critical')\n@el.id('TC-ISS-01')\n"
              "def test_kanban_board():\n"
              "    with el.step('Открыть Issues'):\n        pass\n"
              "    with el.step('Проверить 4 колонки'):\n        pass", "python"),
         h2("Запуск"),
         code("pytest tests/ -v\npytest tests/ --el-no-report\npytest tests/ --el-verbose", "bash"),
     )),
]

def create_articles():
    print("[10] Articles...")
    created = 0
    for title, folder_name, status, content in ARTICLES_DATA:
        folder_id = ART_FOLDERS.get(folder_name)
        r = c.post(ARTICLES_URL, json={
            "title": title,
            "content": content,
            "status": status,
            "folder_id": folder_id,
        })
        d = ok(r, f"article: {title[:40]}")
        if d:
            created += 1
    print(f"  Created: {created}/{len(ARTICLES_DATA)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 11 — TEST PLANS (2)
# ════════════════════════════════════════════════════════════════════════════

def create_test_plans():
    print("[11] Test Plans...")
    plans = [
        ("EL-TP-01: Regression Suite",
         "Полный регрессионный план. Покрывает все основные сценарии "
         "после каждого релиза: Auth, Issues, Articles, QA, Pechkin."),
        ("EL-TP-02: Pechkin Smoke",
         "Smoke-тесты HTTP клиента. Быстрая проверка: GET/POST, auth, variables, runner."),
    ]
    for name, desc in plans:
        r = c.post(TEST_PLANS_URL, json={
            "name": name, "description": desc,
            "project_id": PROJECT_ID, "status": "active",
        })
        ok(r, f"plan: {name[:30]}")
    print(f"  Created: {len(plans)}\n")


# ════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════════════

def summary():
    print("\n" + "═" * 60)
    print("  ErrorLens Project Seeder v3 — COMPLETE")
    print("═" * 60)
    print(f"  Project     : ErrorLens (key=EL)")
    print(f"  Project ID  : {PROJECT_ID}")
    print(f"  Owner       : admin")
    print(f"  Components  : {len(COMPONENTS)}")
    print(f"  Epics       : {len(EPICS)}")
    print(f"  Stories     : {len(STORIES)}")
    print(f"  Bugs        : {len(BUGS)}")
    print(f"  Sprints     : {len(SPRINTS)}")
    print(f"  TC Folders  : {len(TC_FOLDERS)}")
    print(f"  Test Cases  : {len(TC_DATA)}")
    print(f"  Art Folders : {len(ART_FOLDERS)}")
    print(f"  Articles    : {len(ARTICLES_DATA)}")
    print()
    print("  URL: http://192.168.1.74:3000/dashboard/#/issues")
    print("═" * 60)
    with open("/tmp/el_project_id.txt", "w") as f:
        f.write(PROJECT_ID)


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    c.login()
    cleanup()
    load_types()
    create_components()
    create_epics()
    create_stories()
    create_bugs()
    create_sprints()
    create_tc_folders()
    create_testcases()
    create_art_folders()
    create_articles()
    create_test_plans()
    summary()
