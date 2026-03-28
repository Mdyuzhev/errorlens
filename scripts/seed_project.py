#!/usr/bin/env python3
"""
ErrorLens Project Seeder — EL070
Создаёт полный живой проект для dogfooding.
Запуск: python3 scripts/seed_project.py
Env: EL_URL, EL_USERNAME, EL_PASSWORD
"""

import json, os, sys, time, uuid
import requests
from datetime import datetime, timedelta

# ─── Config ──────────────────────────────────────────────────────────────────
BASE_URL = os.getenv("EL_URL", "http://192.168.1.74:3000/api")
USERNAME = os.getenv("EL_USERNAME", "owner1")
PASSWORD = os.getenv("EL_PASSWORD", "Test123!")
DRY_RUN  = os.getenv("DRY_RUN", "0") == "1"

# API paths — nginx strips /api/ prefix, so regular routes at /api/X,
# FastAPI routes with /api/v1/ prefix at /api/api/v1/X
TASKS_URL      = f"{BASE_URL}/tasks"
ARTICLES_URL   = f"{BASE_URL}/articles"
TESTCASES_URL  = f"{BASE_URL}/testcases"
PROJECTS_URL   = f"{BASE_URL}/projects"
SETTINGS_URL   = f"{BASE_URL}/task-settings"
TC_FOLDERS_URL = f"{BASE_URL}/testcases/folders"
ART_FOLDERS_URL= f"{BASE_URL}/articles/folders"
TEST_PLANS_URL = f"{BASE_URL}/v1/test-plans"
SPRINTS_URL    = f"{BASE_URL}/api/v1/sprints"
COMPONENTS_URL = f"{BASE_URL}/api/v1/components"
PECHKIN_URL    = f"{BASE_URL}/api/v1/pechkin"


def uid(): return str(uuid.uuid4())[:8]


class ELClient:
    def __init__(self):
        self.s = requests.Session()
        self.token = None
        self.project_id = None

    def login(self):
        r = self.s.post(f"{BASE_URL}/auth/login",
                        json={"username": USERNAME, "password": PASSWORD})
        r.raise_for_status()
        self.token = r.json()["access_token"]
        self.s.headers["Authorization"] = f"Bearer {self.token}"
        print(f"[AUTH] Logged in as {USERNAME}")

    def get(self, url, **kw):   return self.s.get(url, **kw)
    def post(self, url, **kw):  return self.s.post(url, **kw)
    def put(self, url, **kw):   return self.s.put(url, **kw)
    def delete(self, url, **kw):return self.s.delete(url, **kw)
    def patch(self, url, **kw): return self.s.patch(url, **kw)


c = ELClient()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def tiptap_doc(*blocks):
    """Создать TipTap doc из блоков."""
    return {"type": "doc", "content": list(blocks)}

def heading(level, text):
    return {"type": "heading", "attrs": {"level": level},
            "content": [{"type": "text", "text": text}]}

def paragraph(*texts):
    content = []
    for t in texts:
        if isinstance(t, str):
            content.append({"type": "text", "text": t})
        else:
            content.append(t)
    return {"type": "paragraph", "content": content}

def bold(text): return {"type": "text", "text": text, "marks": [{"type": "bold"}]}
def code_inline(text): return {"type": "text", "text": text, "marks": [{"type": "code"}]}

def bullet_list(*items):
    return {"type": "bulletList", "content": [
        {"type": "listItem", "content": [paragraph(i)]} for i in items
    ]}

def code_block(text, lang="python"):
    return {"type": "codeBlock", "attrs": {"language": lang},
            "content": [{"type": "text", "text": text}]}

def grid_content(*tiptap_blocks):
    """Обернуть tiptap блоки в grid-1 формат."""
    return json.dumps({
        "version": "grid-1",
        "rows": [{
            "id": uid(),
            "columns": [{
                "id": uid(),
                "span": 12,
                "content": tiptap_doc(*tiptap_blocks)
            }]
        }]
    })


def ok(r, label=""):
    if not r.ok:
        print(f"  [WARN] {label}: {r.status_code} — {r.text[:200]}")
        return None
    try:
        return r.json()
    except:
        return {}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 0: CLEANUP — удалить все существующие данные
# ═══════════════════════════════════════════════════════════════════════════

def cleanup():
    print("\n[0] CLEANUP — удаляем все существующие данные...")

    # Получить существующие проекты
    r = c.get(PROJECTS_URL)
    if not r.ok:
        print("  [WARN] Cannot list projects")
        return
    projects = r.json()
    if isinstance(projects, dict):
        projects = projects.get("items", [])

    for proj in projects:
        pid = proj["id"]
        pname = proj["name"]
        print(f"  Cleaning project: {pname} ({pid})")

        # Удалить задачи
        r = c.get(TASKS_URL, params={"project_id": pid, "limit": 500})
        tasks = r.json() if r.ok else []
        tasks = tasks if isinstance(tasks, list) else tasks.get("items", [])
        for t in tasks:
            c.delete(f"{TASKS_URL}/{t['id']}")
        print(f"    Deleted {len(tasks)} tasks")

        # Удалить статьи
        r = c.get(ARTICLES_URL, params={"project_id": pid, "limit": 500})
        arts = r.json() if r.ok else []
        arts = arts if isinstance(arts, list) else arts.get("items", [])
        for a in arts:
            c.delete(f"{ARTICLES_URL}/{a['id']}")
        print(f"    Deleted {len(arts)} articles")

        # Удалить папки статей
        r = c.get(ART_FOLDERS_URL, params={"project_id": pid})
        if r.ok:
            data = r.json()
            folders = data.get("folders", data) if isinstance(data, dict) else data
            def del_folder(f):
                for child in f.get("children", []):
                    del_folder(child)
                c.delete(f"{ART_FOLDERS_URL}/{f['id']}")
            for f in (folders if isinstance(folders, list) else []):
                del_folder(f)

        # Удалить тест-кейсы
        r = c.get(TESTCASES_URL, params={"project_id": pid, "limit": 500})
        tcs = r.json() if r.ok else []
        tcs = tcs if isinstance(tcs, list) else tcs.get("items", [])
        for t in tcs:
            c.delete(f"{TESTCASES_URL}/{t['id']}")
        print(f"    Deleted {len(tcs)} testcases")

        # Удалить папки тест-кейсов
        r = c.get(TC_FOLDERS_URL, params={"project_id": pid})
        if r.ok:
            data = r.json()
            tcf = data.get("folders", data) if isinstance(data, dict) else data
            def del_tcf(f):
                for child in f.get("children", []):
                    del_tcf(child)
                c.delete(f"{TC_FOLDERS_URL}/{f['id']}")
            for f in (tcf if isinstance(tcf, list) else []):
                del_tcf(f)

        # Удалить спринты
        r = c.get(SPRINTS_URL, params={"project_id": pid})
        if r.ok:
            for s in r.json():
                c.delete(f"{SPRINTS_URL}/{s['id']}")

        # Удалить тест-планы
        r = c.get(TEST_PLANS_URL, params={"project_id": pid})
        if r.ok:
            tps = r.json()
            tps = tps if isinstance(tps, list) else tps.get("items", [])
            for tp in tps:
                c.delete(f"{TEST_PLANS_URL}/{tp['id']}")

        # Удалить Pechkin коллекции
        r = c.get(f"{PECHKIN_URL}/collections", params={"project_id": pid})
        if r.ok:
            for col in r.json():
                c.delete(f"{PECHKIN_URL}/collections/{col['id']}")

    print(f"  [DONE] Cleanup complete")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: PROJECT — использовать существующий или создать новый
# ═══════════════════════════════════════════════════════════════════════════

def setup_project():
    print("\n[1] PROJECT setup...")

    r = c.get(PROJECTS_URL)
    projects = r.json() if r.ok else []
    if isinstance(projects, dict):
        projects = projects.get("items", [])

    # Найти или создать проект ErrorLens
    # Deduplicate projects by id
    seen = set()
    unique = []
    for p in projects:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
    projects = unique

    for p in projects:
        if p.get("key") == "EL" or "ErrorLens" in p.get("name", ""):
            c.project_id = p["id"]
            if p["name"] != "ErrorLens":
                c.put(f"{PROJECTS_URL}/{p['id']}", json={"name": "ErrorLens",
                    "description": "Основной проект платформы ErrorLens — AI-powered QA platform"})
            print(f"  Using project: {p['name']} ({c.project_id})")
            return c.project_id

    # Если есть хоть один проект — используем его и переименуем
    if projects:
        p = projects[0]
        c.project_id = p["id"]
        c.put(f"{PROJECTS_URL}/{p['id']}", json={
            "name": "ErrorLens",
            "description": "Основной проект платформы ErrorLens — AI-powered QA platform"
        })
        print(f"  Reusing project: {p['name']} → ErrorLens ({c.project_id})")
        return c.project_id

    # Создать новый
    r = c.post(PROJECTS_URL, json={
        "name": "ErrorLens",
        "key": "EL",
        "description": "Основной проект платформы ErrorLens — AI-powered QA platform для QA-инженеров"
    })
    if r.ok:
        c.project_id = r.json()["id"]
        print(f"  Created project: ErrorLens ({c.project_id})")
    return c.project_id


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: TASK TYPES — получить IDs
# ═══════════════════════════════════════════════════════════════════════════

TYPES = {}  # slug → id

def load_task_types():
    print("\n[2] TASK TYPES...")
    r = c.get(f"{SETTINGS_URL}/types", params={"project_id": c.project_id})
    if not r.ok:
        print(f"  [WARN] Cannot load task types: {r.status_code}")
        return
    for t in r.json():
        TYPES[t["slug"]] = t["id"]
    print(f"  Types: {list(TYPES.keys())}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

COMPONENTS = {}  # name → id

def create_components():
    print("\n[3] COMPONENTS...")
    components_data = [
        ("Authentication",           "JWT-авторизация, refresh токены, мультитенантность"),
        ("Issues & Sprints",         "Задачи, Kanban-доска, бэклог, спринты, JQL"),
        ("Articles",                 "База знаний, GridEditor, версии, PDF-экспорт"),
        ("QA Module",                "Тест-кейсы, тест-планы, прогоны, дашборд покрытия"),
        ("Generator & Pechkin",      "Генераторы тестов: Static, LLM, EVA, HTTP-клиент Pechkin"),
    ]
    for name, desc in components_data:
        r = c.post(COMPONENTS_URL, json={
            "name": name, "description": desc, "project_id": c.project_id
        })
        d = ok(r, f"component {name}")
        if d:
            COMPONENTS[name] = d.get("id", "")
    print(f"  [DONE] {len(COMPONENTS)} components created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: EPICS (6)
# ═══════════════════════════════════════════════════════════════════════════

EPICS = {}  # key → id

def create_epics():
    print("\n[4] EPICS...")
    epics = [
        ("EP-AUTH",  "Аутентификация и безопасность",
         "JWT-авторизация, refresh токены, multi-tenancy и управление пользователями. "
         "Основа всей системы — без надёжной авторизации все остальные модули недоступны.",
         "Authentication"),
        ("EP-ISSUES","Issues и Sprint Management",
         "Полноценный трекер задач в стиле Jira: Kanban-доска, JQL-фильтрация, "
         "бэклог с ранжированием, спринты с burndown, дашборд метрик.",
         "Issues & Sprints"),
        ("EP-ARTICLES","База знаний (Articles)",
         "Confluence-подобная база знаний: иерархия папок, блочный редактор GridEditor, "
         "breadcrumbs, TOC, история версий, PDF-экспорт, импорт из .md/.docx.",
         "Articles"),
        ("EP-QA",    "QA: Управление тестированием",
         "Полноценная TMS в стиле TestIT: тест-кейсы с шагами, тест-планы, прогоны, "
         "матрица результатов, дашборд с трендами и покрытием.",
         "QA Module"),
        ("EP-GEN",   "Генератор тестов (Static, LLM, EVA)",
         "Автоматическая генерация тест-кейсов из OpenAPI-спецификации. "
         "Static-режим (без LLM), LLM-режим (с AI), EVA — оценка качества тестов.",
         "Generator & Pechkin"),
        ("EP-PECHKIN","Pechkin HTTP Client",
         "Встроенный HTTP-клиент в стиле Postman: коллекции, переменные окружения, "
         "auth-типы, Collection Runner, история запросов, импорт Postman JSON.",
         "Generator & Pechkin"),
    ]
    for key, title, desc, component in epics:
        r = c.post(TASKS_URL, json={
            "title": title,
            "description": desc,
            "type_id": TYPES.get("epic"),
            "priority": "high",
            "status": "done",
            "project_id": c.project_id,
            "component_id": COMPONENTS.get(component),
            "labels": [key.lower()],
        })
        d = ok(r, f"epic {title}")
        if d:
            EPICS[key] = d.get("id", "")
    print(f"  [DONE] {len(EPICS)} epics created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: STORIES (18)
# ═══════════════════════════════════════════════════════════════════════════

STORIES = {}  # key → id

STORIES_DATA = [
    # AUTH
    ("ST-AUTH-1", "JWT Login & Token Refresh",
     "Пользователь входит через username/password, получает access_token (15 мин) "
     "и refresh_token (7 дней). При истечении access_token — автоматический refresh "
     "без перезагрузки страницы. При истечении refresh — редирект на /login.",
     "EP-AUTH", "Authentication", "high"),
    ("ST-AUTH-2", "Мультитенантность и изоляция проектов",
     "Каждый пользователь работает в своём проекте. Задачи, статьи и тест-кейсы "
     "одного проекта недоступны пользователям других проектов. Проверка через check_project_access.",
     "EP-AUTH", "Authentication", "high"),
    ("ST-AUTH-3", "Панель администратора",
     "Администратор системы (role=admin) управляет пользователями: создание, "
     "смена пароля, деактивация. Доступно через /settings → Admin.",
     "EP-AUTH", "Authentication", "medium"),

    # ISSUES
    ("ST-ISS-1", "Kanban-доска и JQL-фильтрация",
     "Kanban с 4 колонками (Todo/In Progress/Review/Done), drag-and-drop карточек, "
     "фильтрация по типу задачи. JQL-строка с автодополнением: status = 'todo', "
     "priority = high, assignee = currentUser().",
     "EP-ISSUES", "Issues & Sprints", "high"),
    ("ST-ISS-2", "Бэклог и Sprint Management",
     "Бэклог — список задач без спринта, сортировка по rank. Drag-and-drop для "
     "изменения ранга. Создание, запуск и завершение спринтов. Burndown chart "
     "и velocity по последним 5 спринтам.",
     "EP-ISSUES", "Issues & Sprints", "high"),
    ("ST-ISS-3", "Детальная карточка Issue",
     "Fullscreen просмотр и редактирование: 3 вкладки (Details/Activity/WorkLog), "
     "sidebar (Priority/Severity/Component/StoryPoints/Sprint/People/Time/Labels), "
     "вложения через MinIO, логирование времени, custom fields.",
     "EP-ISSUES", "Issues & Sprints", "high"),

    # ARTICLES
    ("ST-ART-1", "GridEditor и полноэкранный редактор",
     "Блочный редактор на основе grid-1 формата: текст, заголовки, списки, "
     "код с подсветкой, callout-блоки (info/warning/success/note), expand-блоки. "
     "Autosave каждые 60 секунд.",
     "EP-ARTICLES", "Articles", "high"),
    ("ST-ART-2", "Просмотрщик статей (Viewer)",
     "Fullscreen просмотр: breadcrumbs (путь от корня), TOC (H1-H3 с IntersectionObserver), "
     "metadata (автор, дата, просмотры), блок дочерних страниц, тег-облако.",
     "EP-ARTICLES", "Articles", "medium"),
    ("ST-ART-3", "PDF-экспорт и история версий",
     "Экспорт статьи в PDF через weasyprint. История версий — список снапшотов "
     "с возможностью просмотра предыдущей версии в read-only режиме.",
     "EP-ARTICLES", "Articles", "medium"),

    # QA
    ("ST-QA-1", "Управление тест-кейсами",
     "Создание тест-кейсов с шагами (action/expected/data), иерархия папок (max depth 3), "
     "фильтрация по статусу/приоритету, bulk-операции, привязка к Issues.",
     "EP-QA", "QA Module", "high"),
    ("ST-QA-2", "Тест-планы и прогоны",
     "Создание тест-плана с набором кейсов. Запуск прогона: выполнение кейсов по очереди, "
     "запись результата (passed/failed/blocked/skipped), комментарии к упавшим кейсам.",
     "EP-QA", "QA Module", "high"),
    ("ST-QA-3", "QA-дашборд и покрытие",
     "Trend-чарт passed/failed по последним 10 прогонам, distribution по статусам кейсов, "
     "coverage по папкам, топ-5 нестабильных кейсов. Кэш Redis TTL 300s.",
     "EP-QA", "QA Module", "medium"),

    # GENERATOR
    ("ST-GEN-1", "Static генератор из OpenAPI спеки",
     "Парсинг OpenAPI YAML/JSON: extract endpoints, methods, schemas. "
     "Генерация тест-кейсов с happy path + negative cases + placeholder values. "
     "Вывод в pytest/JavaScript/postman форматах.",
     "EP-GEN", "Generator & Pechkin", "medium"),
    ("ST-GEN-2", "LLM и EVA анализаторы",
     "LLM-генератор использует Groq API для умной генерации тестов. "
     "EVA анализирует качество уже существующих тестов: coverage score, "
     "дубликаты, пропущенные edge cases.",
     "EP-GEN", "Generator & Pechkin", "low"),

    # PECHKIN
    ("ST-PECK-1", "Коллекции и управление запросами",
     "Создание коллекций, папок, запросов. Импорт Postman Collection v2.1. "
     "Дерево коллекций с контекстным меню (rename/delete/duplicate). "
     "Все данные хранятся в PostgreSQL.",
     "EP-PECHKIN", "Generator & Pechkin", "high"),
    ("ST-PECK-2", "HTTP-прокси: методы, auth, body",
     "Поддержка GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS. Auth: Bearer, Basic, API Key. "
     "Body: raw JSON, form-data, x-www-form-urlencoded. "
     "Tabs: Params/Headers/Body/Auth/Pre-request/Tests/Code.",
     "EP-PECHKIN", "Generator & Pechkin", "high"),
    ("ST-PECK-3", "Variables, Collection Runner, История",
     "Переменные окружения (scope: global/collection/custom). Подстановка {{varName}} "
     "в URL и headers. Collection Runner — выполнение всех запросов коллекции. "
     "История запросов с status_code и duration.",
     "EP-PECHKIN", "Generator & Pechkin", "medium"),
]

def create_stories():
    print("\n[5] STORIES...")
    for key, title, desc, epic_key, component, priority in STORIES_DATA:
        r = c.post(TASKS_URL, json={
            "title": title,
            "description": desc,
            "type_id": TYPES.get("story"),
            "priority": priority,
            "status": "done",
            "project_id": c.project_id,
            "parent_id": EPICS.get(epic_key),
            "component_id": COMPONENTS.get(component),
            "labels": [key.lower().replace("-","_")],
        })
        d = ok(r, f"story {title}")
        if d:
            STORIES[key] = d.get("id", "")
    print(f"  [DONE] {len(STORIES)} stories created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: BUGS — реальные баги из EL066-069 (15)
# ═══════════════════════════════════════════════════════════════════════════

BUGS = {}  # key → id

BUGS_DATA = [
    # EL066 — Pechkin
    ("BUG-PECK-001", "Method selector не обновляет v-model",
     "Кастомный CSS-dropdown для выбора HTTP метода не вызывает нативный change event "
     "на <select v-model=\"req.method\">. Визуально метод выбран, но req.method "
     "остаётся 'GET'. Все POST/PUT/DELETE запросы отправляются как GET.",
     "critical", "ST-PECK-2", "EL066"),
    ("BUG-PECK-002", "Variables API PUT → 500 Internal Server Error",
     "Endpoint PUT /api/v1/pechkin/collections/{id}/variables возвращает 500. "
     "Upsert_variable использует INSERT ON CONFLICT без нужного уникального "
     "constraint в схеме. Переменные окружения полностью нефункциональны.",
     "critical", "ST-PECK-3", "EL066"),
    ("BUG-PECK-003", "Mode switcher кнопки не реагируют на обычный click",
     "Кнопки Static/LLM/EVA/Pechkin в SpecGeneratorTab не переключаются стандартным "
     "кликом — требуется element.click() через JavaScript. Причина: z-index или "
     "pointer-events на вложенном span перехватывает клики.",
     "critical", "ST-GEN-1", "EL066"),
    ("BUG-PECK-004", "form-data сериализация через JSON.stringify (неправильно)",
     "В RequestEditor.vue функция send() использует JSON.stringify() для x-www-form-urlencoded. "
     "Правильно: new URLSearchParams().toString() для urlencoded, FormData для form-data.",
     "high", "ST-PECK-2", "EL066"),
    ("BUG-PECK-005", "syncParamsToUrl ломается при URL с переменными {{varName}}",
     "new URL('{{baseUrl}}/api') бросает TypeError. Params не синхронизируются "
     "с URL когда URL содержит переменные. catch блок молча проглатывает ошибку.",
     "high", "ST-PECK-3", "EL066"),

    # EL067 — Pechkin Fixes
    ("BUG-PECK-006", "History status_code показывает 0 вместо реального кода",
     "После выполнения 200 GET запроса вкладка History показывает статус '0' "
     "вместо '200'. history_to_dict не маппит поле correctly.",
     "medium", "ST-PECK-3", "EL067"),

    # EL068 — Issues & Articles
    ("BUG-ISS-001", "JQL GET /tasks?jql=status='todo' → 500",
     "JQL компилятор крашится на валидном запросе с кавычками. Неперехваченное "
     "исключение в list_tasks_jql или _resolve_value. Фильтрация задач через JQL "
     "полностью недоступна.",
     "critical", "ST-ISS-1", "EL068"),
    ("BUG-ART-001", "PDF export /articles/{id}/export/pdf → 500",
     "weasyprint.HTML(string=html_content).write_pdf() падает с неперехваченным "
     "исключением. Нет try/except вокруг генерации. Также нет проверки установлен "
     "ли weasyprint (ImportError).",
     "critical", "ST-ART-3", "EL068"),
    ("BUG-ISS-002", "Sprints API 404 — нет эндпоинтов start и complete",
     "POST /api/v1/sprints/{id}/start и POST /api/v1/sprints/{id}/complete "
     "возвращают 404. Роутер зарегистрирован, но эти два хэндлера не реализованы. "
     "Весь модуль спринтов недоступен.",
     "high", "ST-ISS-2", "EL068"),
    ("BUG-ISS-003", "POST /tasks без project_id → 500",
     "TaskCreate.project_id опциональный, но при None — IntegrityError в БД. "
     "Нет fallback на default_project пользователя (в отличие от articles). "
     "58 Cypress тестов каскадно упали из-за этого.",
     "high", "ST-ISS-1", "EL068"),
    ("BUG-ISS-004", "Work-logs API 404 — неверный путь в тестах",
     "Тесты вызывали /tasks/{id}/work-logs но реальный путь: "
     "POST /api/v1/work-logs (с issue_id в теле), GET /api/v1/work-logs/issues/{id}.",
     "high", "ST-ISS-3", "EL068"),
    ("BUG-ART-002", "DOCX import → 500 (python-docx exception)",
     "При импорте .docx файла исключение из python-docx не перехватывается. "
     "Весь import endpoint падает с 500 вместо корректного error message.",
     "medium", "ST-ART-1", "EL068"),
    ("BUG-ART-003", "FolderTree context menu отсутствует",
     "Cypress тест ищет .context-menu но реальный класс .ctx-menu. "
     "Right-click на папке не открывает меню rename/delete в части окружений.",
     "medium", "ST-ART-1", "EL068"),
    ("BUG-ISS-005", "Dashboard stats структура: top_assignees vs by_assignee",
     "GET /tasks/dashboard/stats возвращает ключ 'by_assignee' а не 'top_assignees' "
     "как ожидается в тестах и документации.",
     "medium", "ST-ISS-1", "EL068"),
    ("BUG-PECK-007", "collectAllRequests не рекурсивный для 3+ уровней",
     "CollectionTree.vue collectAllRequests() обходит только folders[].children[], "
     "но не folders[].children[].children[]. Запросы из 3-го уровня вложенности "
     "не попадают в Collection Runner.",
     "low", "ST-PECK-1", "EL066"),
]

def create_bugs():
    print("\n[6] BUGS...")
    for key, title, desc, severity, story_key, sprint_label in BUGS_DATA:
        r = c.post(TASKS_URL, json={
            "title": title,
            "description": desc,
            "type_id": TYPES.get("bug"),
            "priority": "high" if severity in ("critical", "high") else "medium",
            "severity": severity,
            "status": "done",
            "project_id": c.project_id,
            "parent_id": STORIES.get(story_key),
            "labels": [key.lower().replace("-","_"), sprint_label.lower()],
        })
        d = ok(r, f"bug {key}")
        if d:
            BUGS[key] = d.get("id", "")
    print(f"  [DONE] {len(BUGS)} bugs created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: SPRINTS (4 завершённых + 1 активный)
# ═══════════════════════════════════════════════════════════════════════════

SPRINTS = {}

def create_sprints():
    print("\n[7] SPRINTS...")

    sprints_data = [
        ("EL-QA-1: Pechkin Audit",
         "Полный QA-аудит раздела Pechkin HTTP Client. 181 тест написан и прогнан, "
         "найдено 12 багов. Pass rate: 40%.",
         "2026-02-01", "2026-02-14", "completed"),
        ("EL-FIX-1: Pechkin Fixes",
         "Исправление 12 багов Pechkin: method selector, variables API 500, "
         "mode switcher, form-data serialization, syncParamsToUrl.",
         "2026-02-15", "2026-02-28", "completed"),
        ("EL-QA-2: Issues & Articles Audit",
         "QA Issues и Articles разделов. 325 тестов, 15 багов. "
         "JQL 500, PDF 500, Sprints 404, Work-logs 404.",
         "2026-03-01", "2026-03-14", "completed"),
        ("EL-FIX-2: Issues & Articles Fixes",
         "Исправление 15 багов: JQL exception handler, Sprints start/complete, "
         "PDF try/except, POST tasks project_id fallback.",
         "2026-03-15", "2026-03-28", "active"),
    ]

    for name, goal, start, end, status in sprints_data:
        r = c.post(SPRINTS_URL, json={
            "name": name,
            "goal": goal,
            "start_date": start,
            "end_date": end,
            "project_id": c.project_id,
        })
        d = ok(r, f"sprint {name}")
        if not d:
            continue
        sid = d.get("id", "")
        SPRINTS[name[:8]] = sid

        # Стартовать и завершить спринт (для истории)
        if status in ("active", "completed"):
            c.post(f"{SPRINTS_URL}/{sid}/start")
        if status == "completed":
            c.post(f"{SPRINTS_URL}/{sid}/complete", json={})

    print(f"  [DONE] {len(SPRINTS)} sprints created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: TEST CASE FOLDERS
# ═══════════════════════════════════════════════════════════════════════════

TC_FOLDERS = {}  # name → id

def create_tc_folders():
    print("\n[8] TESTCASE FOLDERS...")
    pid = c.project_id

    structure = {
        "Authentication": [],
        "Issues": ["Board & Kanban", "Backlog & Sprints", "Issue Detail", "Dashboard"],
        "Articles": ["Editor & GridEditor", "Viewer & Navigation", "Folder Management"],
        "QA Module": ["Test Cases CRUD", "Test Plans & Runs", "QA Dashboard"],
        "Generator": ["Static Generator", "Pechkin HTTP Client", "LLM & EVA"],
        "API Tests": ["Issues API", "Articles API", "Pechkin API", "QA API"],
    }

    for parent_name, children in structure.items():
        r = c.post(TC_FOLDERS_URL, json={
            "name": parent_name,
            "project_id": pid
        })
        d = ok(r, f"tc_folder {parent_name}")
        if not d:
            continue
        parent_id = d.get("id", "")
        TC_FOLDERS[parent_name] = parent_id

        for child_name in children:
            r2 = c.post(TC_FOLDERS_URL, json={
                "name": child_name,
                "parent_id": parent_id,
                "project_id": pid
            })
            d2 = ok(r2, f"tc_folder {child_name}")
            if d2:
                TC_FOLDERS[child_name] = d2.get("id", "")

    print(f"  [DONE] {len(TC_FOLDERS)} testcase folders created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: TEST CASES (45) — один на каждый describe-блок
# ═══════════════════════════════════════════════════════════════════════════

def make_steps(*steps):
    """Создать список шагов тест-кейса."""
    return [{"action": a, "expected": e, "data": d}
            for a, e, d in steps]

TESTCASES_DATA = [
    # ── AUTHENTICATION (folder) ─────────────────────────────────────────────
    ("TC-AUTH-01", "Login: успешная авторизация",
     "Проверить что пользователь с валидными credentials получает JWT токен и редиректируется на дашборд",
     "Authentication", "critical", [
         ("Открыть http://192.168.1.74:3000/dashboard/#/login", "Открыта страница логина с полями username/password", None),
         ("Ввести username: owner1, password: Test123!", "Поля заполнены корректно", "owner1 / Test123!"),
         ("Нажать кнопку Submit/Войти", "Выполняется POST /auth/login", None),
         ("Дождаться ответа", "Статус 200, access_token в localStorage, редирект на /dashboard", None),
     ]),
    ("TC-AUTH-02", "Login: невалидные credentials → 401",
     "Проверить что при неверном пароле показывается ошибка и пользователь остаётся на /login",
     "Authentication", "high", [
         ("Открыть страницу /login", "Страница логина видна", None),
         ("Ввести username: owner1, password: wrongpassword", "Поля заполнены", "owner1 / wrongpassword"),
         ("Нажать Submit", "Запрос POST /auth/login → 401", None),
         ("Наблюдать UI", "Показывается сообщение об ошибке. URL остаётся /login. Токен НЕ сохранён", None),
     ]),
    ("TC-AUTH-03", "Auth Guard: редирект неавторизованного пользователя",
     "Проверить что обращение к защищённому маршруту без токена редиректит на /login",
     "Authentication", "high", [
         ("Очистить localStorage (удалить access_token)", "localStorage пуст", None),
         ("Перейти на /dashboard/#/issues", "Выполняется навигация", None),
         ("Наблюдать URL", "Редирект на /login. Страница Issues НЕ показана", None),
     ]),
    ("TC-AUTH-04", "JWT Refresh: автоматическое обновление токена",
     "Проверить что при 401 ответе axios автоматически делает refresh и повторяет запрос",
     "Authentication", "medium", [
         ("Установить в localStorage истёкший access_token (exp в прошлом)", "Токен установлен", None),
         ("Выполнить API запрос через интерфейс (например, открыть Issues)", "Запрос уходит с истёкшим токеном", None),
         ("Interceptor получает 401", "Автоматически вызывается POST /auth/refresh", None),
         ("Новый токен сохранён, исходный запрос повторён", "Страница загрузилась без перехода на /login", None),
     ]),

    # ── ISSUES: Board & Kanban ─────────────────────────────────────────────
    ("TC-ISS-01", "Kanban Board: отображение 4 колонок",
     "Проверить что Kanban-доска содержит все 4 колонки с корректными заголовками",
     "Board & Kanban", "critical", [
         ("Открыть /dashboard/#/issues", "Страница Issues загружена, вкладка Board активна", None),
         ("Осмотреть Kanban-доску", "Видны 4 колонки: To Do, In Progress, Review, Done", None),
         ("Проверить счётчики", "Каждая колонка показывает количество задач в скобках", None),
         ("Проверить карточки", "Карточки содержат: полосу приоритета, human_id, title, assignee, severity", None),
     ]),
    ("TC-ISS-02", "Kanban: drag-and-drop между колонками",
     "Проверить что перетаскивание карточки меняет статус задачи",
     "Board & Kanban", "high", [
         ("Создать задачу со статусом 'todo'", "Задача появилась в колонке To Do", None),
         ("Перетащить карточку из To Do в In Progress", "Drag start на карточке, drop в колонку In Progress", None),
         ("Наблюдать API запрос", "PUT /tasks/{id} с {status: 'in_progress'} → 200", None),
         ("Проверить результат", "Карточка переместилась в In Progress. Счётчики обновились", None),
     ]),
    ("TC-ISS-03", "JQL фильтрация: валидный запрос",
     "Проверить что JQL запрос фильтрует задачи и переключает вид на List",
     "Board & Kanban", "high", [
         ("Открыть Issues → вкладка Board", "JQL Bar видна над доской", None),
         ("Ввести: status = 'todo'", "Текст введён в JQL Bar", "status = \"todo\""),
         ("Нажать Enter или Apply", "GET /tasks?jql=status='todo'&project_id=... → 200 (не 500!)", None),
         ("Наблюдать вид", "Режим автоматически переключился на List. Показаны только todo задачи", None),
     ]),
    ("TC-ISS-04", "JQL: невалидный синтаксис → 400 с сообщением",
     "Проверить что JQL с ошибкой синтаксиса показывает понятное сообщение, не 500",
     "Board & Kanban", "medium", [
         ("Ввести в JQL Bar: abc %%% xyz", "Текст введён", "abc %%% xyz"),
         ("Нажать Enter", "POST /tasks?jql=abc+%%%+xyz → 400 (не 500!)", None),
         ("Проверить UI", "Показано сообщение об ошибке синтаксиса. Приложение не крашнулось", None),
     ]),

    # ── ISSUES: Backlog & Sprints ─────────────────────────────────────────
    ("TC-ISS-05", "Backlog: список и ранжирование",
     "Проверить что вкладка Backlog показывает задачи без спринта, отсортированные по rank",
     "Backlog & Sprints", "high", [
         ("Перейти на вкладку Backlog", "BacklogView загружен, список задач виден", None),
         ("Найти задачу в списке", "Строки содержат: human_id, title, type, status, priority, assignee", None),
         ("Drag-and-drop задачу вверх/вниз", "PATCH /tasks/{id}/rank выполнен. Список перерисован", None),
     ]),
    ("TC-ISS-06", "Sprint: создание и запуск",
     "Проверить полный цикл жизни спринта: создание → запуск → завершение",
     "Backlog & Sprints", "high", [
         ("Нажать + Create Sprint в Backlog", "Открылась форма создания спринта", None),
         ("Заполнить: Name='Test Sprint', Start=today, End=+14 дней", "Форма заполнена", None),
         ("Submit", "POST /api/v1/sprints → 201. Sprint Panel появился над Backlog", None),
         ("Нажать Start Sprint", "POST /api/v1/sprints/{id}/start → 200. Статус = active", None),
         ("Нажать Complete Sprint", "POST /api/v1/sprints/{id}/complete → 200. Sprint завершён", None),
         ("Проверить velocity", "GET /api/v1/sprints/velocity содержит данные этого спринта", None),
     ]),

    # ── ISSUES: Issue Detail ─────────────────────────────────────────────
    ("TC-ISS-07", "Создание Issue через модальное окно",
     "Проверить создание задачи со всеми полями через + New Issue",
     "Issue Detail", "critical", [
         ("Нажать кнопку + New Issue", "Открылось модальное окно создания", None),
         ("Заполнить Title: 'E2E Test Issue'", "Title введён", "E2E Test Issue"),
         ("Выбрать Type=Bug, Priority=High, Severity=Critical", "Поля заполнены", None),
         ("Заполнить Labels: 'e2e, cypress'", "Labels введены", "e2e, cypress"),
         ("Нажать Create", "POST /tasks → 200. human_id присвоен. Модал закрылся", None),
         ("Найти задачу в Kanban To Do", "Задача видна в колонке, показывает severity badge", None),
     ]),
    ("TC-ISS-08", "IssueDetailView: редактирование и сохранение",
     "Проверить редактирование задачи через fullscreen детальный вид",
     "Issue Detail", "high", [
         ("Кликнуть на карточку задачи", "TaskViewer открылся в overlay", None),
         ("Нажать Edit", "IssueDetailView открылся. Поля переключились в edit mode", None),
         ("Изменить Title, Priority=High, Story Points=5", "Поля изменены", None),
         ("Нажать Save", "PUT /tasks/{id} → 200. Изменения сохранены", None),
         ("Закрыть и открыть снова", "Все изменения персистентны", None),
     ]),
    ("TC-ISS-09", "WorkLog: логирование времени",
     "Проверить добавление записи о затраченном времени",
     "Issue Detail", "medium", [
         ("Открыть IssueDetailView → вкладка Work Log", "WorkLogBlock виден", None),
         ("Нажать Log Work", "Форма открылась: hours, date, comment", None),
         ("Заполнить: 2.5 часа, дата сегодня, комментарий", "Поля заполнены", "2.5h / today"),
         ("Submit", "POST /api/v1/work-logs → 201. spent_hours задачи обновился", None),
         ("Проверить прогресс-бар", "estimated vs spent отображается корректно", None),
     ]),

    # ── ISSUES: Dashboard ─────────────────────────────────────────────────
    ("TC-ISS-10", "Dashboard: загрузка stats и кэш",
     "Проверить что dashboard stats загружается и использует Redis кэш",
     "Dashboard", "medium", [
         ("Перейти на вкладку Dashboard", "GET /tasks/dashboard/stats?project_id=... → 200", None),
         ("Проверить response header", "X-Cache: MISS при первом запросе", None),
         ("Обновить Dashboard", "Повторный запрос → X-Cache: HIT", None),
         ("Проверить UI", "Чарты отображены: by_type, by_priority. Нет краша", None),
     ]),

    # ── ARTICLES: Editor & GridEditor ─────────────────────────────────────
    ("TC-ART-01", "Создание статьи: fullscreen editor",
     "Проверить создание новой статьи через fullscreen GridEditor",
     "Editor & GridEditor", "critical", [
         ("Открыть Articles, нажать + New Article", "Fullscreen editor открылся", None),
         ("Ввести title: 'Тестовая статья'", "Title input заполнен", None),
         ("Нажать ▼ Meta, заполнить Category: 'Testing'", "Subheader появился, category заполнена", None),
         ("Добавить контент в GridEditor", "Блок с текстом добавлен", None),
         ("Нажать Save", "POST /articles → 200. Slug присвоен. Editor закрылся", None),
         ("Найти статью в списке", "Статья видна со статусом draft", None),
     ]),
    ("TC-ART-02", "Autosave при редактировании",
     "Проверить что autosave срабатывает при редактировании существующей статьи",
     "Editor & GridEditor", "medium", [
         ("Открыть существующую статью → Edit", "Editor открылся с данными статьи", None),
         ("Изменить содержимое", "isDirty = true", None),
         ("Подождать 60 секунд (или проверить таймер)", "Статус 'Сохранение...' появляется", None),
         ("Через 2-3 сек", "Статус '✓ Сохранено HH:MM' → PUT /articles/{id} → 200", None),
     ]),
    ("TC-ART-03", "Import .md файла в статью",
     "Проверить импорт Markdown-файла через кнопку Import",
     "Editor & GridEditor", "medium", [
         ("Нажать Import в списке статей", "File picker открылся (accept='.md,.docx')", None),
         ("Выбрать .md файл < 5MB", "Файл выбран", "test-article.md"),
         ("POST /articles/import → 200", "Alert 'Article imported: ...'", None),
         ("Найти в списке", "Статья создана со статусом draft, title из H1 файла", None),
     ]),
    ("TC-ART-04", "Import: файл > 5MB → ошибка",
     "Проверить валидацию размера файла при импорте",
     "Editor & GridEditor", "low", [
         ("Нажать Import", "File picker открылся", None),
         ("Выбрать файл > 5MB", "Файл выбран", ">5MB file"),
         ("Наблюдать UI", "Alert 'File too large. Max: 5 MB'. Файл НЕ импортирован", None),
     ]),

    # ── ARTICLES: Viewer & Navigation ─────────────────────────────────────
    ("TC-ART-05", "ArticleViewer: breadcrumbs и metadata",
     "Проверить отображение breadcrumbs, meta и статус-бейджа в просмотрщике",
     "Viewer & Navigation", "high", [
         ("Создать статью в папке Level1/Level2", "Статья создана в подпапке", None),
         ("Открыть статью кликом из списка", "ArticleViewer открылся fullscreen", None),
         ("Проверить breadcrumbs", "Показаны: Articles › Level1 › Level2 › Название", None),
         ("Кликнуть на Level1 в breadcrumbs", "Навигация в папку Level1. Статьи Level1 в списке", None),
         ("Проверить meta строку", "Показаны: автор, дата, N просмотров", None),
     ]),
    ("TC-ART-06", "TOC: автогенерация и IntersectionObserver",
     "Проверить что TOC строится из H1-H3 заголовков и подсвечивает активный раздел",
     "Viewer & Navigation", "medium", [
         ("Открыть статью с H1, H2, H3 заголовками при ширине >= 1280px", "TOC видна справа", None),
         ("Проверить TOC items", "Пункты соответствуют заголовкам статьи", None),
         ("Кликнуть на пункт TOC", "Страница прокрутилась к заголовку (smooth scroll)", None),
         ("Прокрутить к H2 разделу", "Соответствующий пункт TOC подсвечен (класс active)", None),
         ("Уменьшить окно до < 1280px", "TOC скрыта. Контент занимает 100% ширины", None),
     ]),
    ("TC-ART-07", "PDF Export",
     "Проверить экспорт статьи в PDF через кнопку PDF",
     "Viewer & Navigation", "high", [
         ("Открыть статью в ArticleViewer", "Viewer открыт с кнопкой PDF", None),
         ("Нажать кнопку PDF", "GET /articles/{id}/export/pdf → 200 (не 500!)", None),
         ("Браузер начинает скачивание", "Файл {slug}.pdf скачивается. Content-Type: application/pdf", None),
         ("Открыть PDF", "Содержит заголовок, breadcrumbs, дату генерации и содержимое", None),
     ]),
    ("TC-ART-08", "История версий",
     "Проверить открытие панели истории и просмотр предыдущей версии",
     "Viewer & Navigation", "medium", [
         ("Отредактировать и сохранить статью 3 раза", "3 версии созданы в article_versions", None),
         ("Открыть статью, нажать 'История'", "Sliding panel открылась справа", None),
         ("GET /articles/{id}/versions → список версий", "Список из 3 элементов с датами", None),
         ("Кликнуть на версию 1", "GET /articles/{id}/versions/{v1} → 200 с content", None),
         ("Version preview показан", "GridEditor в readonly режиме с содержимым v1", None),
     ]),

    # ── ARTICLES: Folder Management ─────────────────────────────────────
    ("TC-ART-09", "FolderTree CRUD",
     "Проверить создание, переименование и удаление папок статей",
     "Folder Management", "high", [
         ("Нажать + в FolderTree sidebar", "Создалась папка с именем по умолчанию", None),
         ("Ввести имя 'Тестовая папка'", "POST /articles/folders → папка создана", None),
         ("Right-click → Rename", "Inline input или prompt для нового имени", None),
         ("Ввести новое имя, сохранить", "PUT /articles/folders/{id} → имя обновлено в дереве", None),
         ("Right-click → Delete, подтвердить", "DELETE /articles/folders/{id} → папка удалена", None),
     ]),
    ("TC-ART-10", "Drag-and-drop статьи в папку",
     "Проверить перемещение статьи в папку через drag-and-drop",
     "Folder Management", "medium", [
         ("Создать статью и папку", "Статья в корне, папка в дереве", None),
         ("Начать drag на строке статьи (draggable=true)", "dataTransfer установлен: type='article', id=...", None),
         ("Drop на папку в FolderTree", "POST /articles/{id}/move-to-folder → 200", None),
         ("Кликнуть на папку в sidebar", "Статья теперь в этой папке", None),
     ]),

    # ── QA: Test Cases CRUD ─────────────────────────────────────────────
    ("TC-QA-01", "Создание тест-кейса с шагами",
     "Проверить создание тест-кейса с табличными шагами через StepsEditor",
     "Test Cases CRUD", "critical", [
         ("Открыть QA → Tree → + New Test Case", "Форма/модал создания открылся", None),
         ("Заполнить Title, Priority, Automation Status", "Поля заполнены", None),
         ("Открыть StepsEditor, нажать + Step", "Новая строка в таблице action/expected/data", None),
         ("Заполнить шаги (3 шага)", "3 строки в таблице с action и expected", None),
         ("Сохранить", "POST /testcases → 200. steps в JSON [{action,expected,data}]", None),
     ]),
    ("TC-QA-02", "Bulk-операции над тест-кейсами",
     "Проверить выбор нескольких кейсов и добавление в тест-план",
     "Test Cases CRUD", "high", [
         ("Открыть QA → Tree", "Список кейсов с чекбоксами", None),
         ("Выбрать 3 кейса через checkbox", "Toolbar с bulk-операциями появился", None),
         ("Нажать 'Add to Plan'", "Выбор тест-плана из списка", None),
         ("Выбрать план и подтвердить", "3 кейса добавлены в план. Counter плана обновился", None),
     ]),

    # ── QA: Test Plans & Runs ─────────────────────────────────────────
    ("TC-QA-03", "Создание тест-плана и запуск прогона",
     "Проверить создание плана, добавление кейсов и запуск прогона",
     "Test Plans & Runs", "critical", [
         ("QA → Test Plans → + New Plan", "Форма создания плана", None),
         ("Заполнить название, сохранить", "POST /v1/test-plans → 201", None),
         ("Добавить 5 тест-кейсов в план", "POST /v1/test-plans/{id}/cases → кейсы добавлены", None),
         ("Нажать Start Run", "Прогон создан. Переход на экран выполнения", None),
         ("Отметить 3 кейса passed, 2 failed", "Статусы записаны для каждого кейса", None),
         ("Нажать Finish Run", "POST /v1/test-plans/runs/{id}/finish → прогон завершён", None),
     ]),
    ("TC-QA-04", "Матрица результатов RunsMatrix",
     "Проверить что матрица результатов показывает кейсы x прогоны с цветовой индикацией",
     "Test Plans & Runs", "high", [
         ("Провести 3 прогона плана с разными результатами", "3 прогона в истории", None),
         ("Открыть детальный вид плана", "RunsMatrix видна под списком кейсов", None),
         ("Проверить структуру матрицы", "Строки = кейсы, столбцы = прогоны (последние 10)", None),
         ("Проверить цвета ячеек", "green=passed, red=failed, orange=blocked, grey=skipped", None),
     ]),

    # ── QA: QA Dashboard ─────────────────────────────────────────────
    ("TC-QA-05", "QA Dashboard: trend и coverage",
     "Проверить отображение trend-чарта и coverage по папкам",
     "QA Dashboard", "medium", [
         ("Перейти QA → Dashboard после нескольких прогонов", "Trend-чарт (Chart.js Line) виден", None),
         ("Проверить данные trend", "Оси X=прогоны, Y=% passed. Минимум 1 точка", None),
         ("Проверить coverage bar chart", "Проценты покрытия по папкам", None),
         ("Повторный запрос dashboard", "GET /api/v1/qa/dashboard → X-Cache: HIT (Redis TTL 300s)", None),
     ]),

    # ── GENERATOR: Static Generator ─────────────────────────────────────
    ("TC-GEN-01", "Static генератор: парсинг OpenAPI",
     "Проверить парсинг OpenAPI YAML/JSON спецификации и генерацию тестов",
     "Static Generator", "high", [
         ("Открыть Generator → Static → вкладка Paste", "Textarea для OpenAPI spec", None),
         ("Вставить минимальный OpenAPI YAML (1 endpoint)", "Spec введена", None),
         ("Нажать Generate (или автоматически)", "Парсинг спецификации выполнен", None),
         ("Выбрать endpoint из списка", "Список эндпоинтов слева", None),
         ("Проверить сгенерированный код", "pytest код с happy path + negative cases виден справа", None),
     ]),
    ("TC-GEN-02", "Static: переключение Framework (pytest/JS/Postman)",
     "Проверить что смена framework меняет синтаксис сгенерированного кода",
     "Static Generator", "medium", [
         ("После парсинга выбрать Framework=pytest", "Код в синтаксисе pytest", None),
         ("Переключить на JavaScript", "Код в синтаксисе fetch/Jest", None),
         ("Переключить на Postman", "Код в виде Postman collection JSON", None),
         ("Переключить обратно на pytest", "Код снова в pytest синтаксисе", None),
     ]),

    # ── GENERATOR: Pechkin HTTP Client ─────────────────────────────────
    ("TC-PECK-01", "Pechkin: отправка GET запроса",
     "Проверить базовую отправку GET запроса и отображение ответа",
     "Pechkin HTTP Client", "critical", [
         ("Открыть Generator → Pechkin", "Collections дерево + редактор виден", None),
         ("Создать новый запрос в коллекции", "Редактор открылся с пустым URL", None),
         ("Ввести URL: https://httpbin.org/get, метод GET", "URL введён, метод выбран", None),
         ("Нажать Send", "POST /api/v1/pechkin/execute → 200", None),
         ("Проверить ответ", "Status 200, duration > 0, JSON body в Pretty режиме", None),
     ]),
    ("TC-PECK-02", "Pechkin: все HTTP методы",
     "Проверить что все 7 HTTP методов работают корректно",
     "Pechkin HTTP Client", "high", [
         ("Выбрать метод POST, URL: httpbin.org/post, добавить body {test:1}", "Конфиг запроса", "POST + JSON body"),
         ("Send → 200", "POST запрос успешен", None),
         ("Аналогично проверить PUT, PATCH, DELETE", "Все методы возвращают 200 от httpbin", None),
         ("HEAD запрос", "200, пустое тело", None),
         ("OPTIONS запрос", "200 или 204", None),
     ]),
    ("TC-PECK-03", "Pechkin: Bearer Auth",
     "Проверить что Bearer token добавляется в Authorization header",
     "Pechkin HTTP Client", "high", [
         ("Открыть вкладку Auth → выбрать Bearer Token", "Поле Token появилось", None),
         ("Ввести token: test-token-123", "Token введён", "test-token-123"),
         ("Send запрос на httpbin.org/get", "Выполнен запрос", None),
         ("Проверить ответ", "В response.headers виден Authorization: Bearer test-token-123", None),
     ]),
    ("TC-PECK-04", "Pechkin: Variables — подстановка {{varName}}",
     "Проверить что переменные подставляются в URL перед отправкой",
     "Pechkin HTTP Client", "high", [
         ("Открыть Variables Panel (gear рядом с ENV selector)", "Panel открылась", None),
         ("Добавить переменную: baseUrl = https://httpbin.org", "Переменная сохранена", None),
         ("Установить URL: {{baseUrl}}/get", "URL с переменной введён", None),
         ("Send", "URL разрешился в https://httpbin.org/get. Запрос успешен (200)", None),
     ]),
    ("TC-PECK-05", "Pechkin: Code Generation (curl/Python/JavaScript)",
     "Проверить что вкладка Code генерирует корректный код для всех языков",
     "Pechkin HTTP Client", "medium", [
         ("Настроить POST запрос с body {key: value} и Authorization header", "Запрос настроен", None),
         ("Открыть вкладку Code → cURL", "curl -X POST 'https://...' -H 'Authorization: Bearer ...' -d '{...}'", None),
         ("Переключить на Python", "import requests; resp = requests.post(..., json={'key': 'value'})", None),
         ("Переключить на JavaScript", "const resp = await fetch('...', {method: 'POST', ...})", None),
         ("Нажать Copy", "Код скопирован в буфер без ошибок", None),
     ]),
    ("TC-PECK-06", "Pechkin: Collection Runner",
     "Проверить запуск всех запросов коллекции через Collection Runner",
     "Pechkin HTTP Client", "medium", [
         ("Создать коллекцию с 3 GET запросами к httpbin.org", "Коллекция с 3 запросами", None),
         ("Нажать play рядом с коллекцией", "Collection Runner modal открылся", None),
         ("Нажать Run", "Запросы выполняются последовательно. Прогресс-бар растёт", None),
         ("После завершения", "Результаты: status_code, duration, passed/failed для каждого", None),
         ("Нажать Export CSV", "CSV файл скачивается с результатами", None),
     ]),

    # ── API Tests: Issues API ─────────────────────────────────────────
    ("TC-API-01", "API: Issues CRUD",
     "Проверить полный цикл CRUD для задач через API",
     "Issues API", "critical", [
         ("POST /tasks {title, priority, project_id} → 200", "Task создан, human_id присвоен", None),
         ("GET /tasks/{id} → 200", "Полный объект: attachments, work_logs, custom_field_values", None),
         ("PUT /tasks/{id} {title: 'Updated'} → 200", "Title обновлён", None),
         ("GET /tasks/{id} → title = 'Updated'", "Изменения персистентны", None),
         ("DELETE /tasks/{id} → 200", "Task удалён", None),
         ("GET /tasks/{id} → 404", "Task не найден", None),
     ]),
    ("TC-API-02", "API: Kanban Board структура",
     "Проверить что GET /tasks/board возвращает правильную структуру",
     "Issues API", "high", [
         ("GET /tasks/board → 200", "Объект с ключами: todo, in_progress, review, done", None),
         ("Каждый ключ → array", "Массив task объектов", None),
         ("GET /tasks/board?type_slug=bug → 200", "Только Bug задачи во всех колонках", None),
         ("Создать задачу, GET /tasks/board", "Задача видна в board.todo", None),
     ]),
    ("TC-API-03", "API: JQL не возвращает 500",
     "Проверить что JQL endpoint возвращает 400 на ошибку, не 500",
     "Issues API", "critical", [
         ("GET /tasks?jql=status = 'todo' → 200 или 400", "НЕ 500!", "Валидный JQL"),
         ("GET /tasks?jql=abc %%% xyz → 400", "error.jql_syntax_error в detail", "Невалидный JQL"),
         ("GET /tasks?jql=priority = high → 200", "Задачи с high priority", None),
     ]),

    # ── API Tests: Articles API ─────────────────────────────────────────
    ("TC-API-04", "API: Articles CRUD",
     "Проверить полный цикл создания, обновления и удаления статей",
     "Articles API", "critical", [
         ("POST /articles {title, content: grid-1 JSON} → 200", "id и slug в ответе", None),
         ("GET /articles/{id} → 200", "Полный объект с content, status, tags", None),
         ("PUT /articles/{id} {status: 'published'} → 200", "Статус обновлён", None),
         ("GET /articles → список содержит новую статью", "Статья видна в списке", None),
         ("DELETE /articles/{id} → 200", "Статья удалена", None),
     ]),
    ("TC-API-05", "API: PDF Export не 500",
     "Проверить что PDF endpoint возвращает PDF или 501, не 500",
     "Articles API", "critical", [
         ("Создать статью с контентом", "article_id получен", None),
         ("GET /articles/{id}/export/pdf → не 500", "Статус 200 (PDF) или 501 (weasyprint не установлен)", None),
         ("Если 200: Content-Type: application/pdf", "Валидный PDF файл", None),
         ("Если 501: понятное сообщение об ошибке", "НЕ 500 Internal Server Error", None),
     ]),
    ("TC-API-06", "API: Versions — история изменений",
     "Проверить сохранение и получение версий статей",
     "Articles API", "high", [
         ("Создать статью, обновить 3 раза через PUT", "3 версии в article_versions", None),
         ("GET /articles/{id}/versions → список из 3", "Каждая версия: id, title, saved_by, created_at", None),
         ("GET /articles/{id}/versions/{v_id} → 200", "Объект с content (snapshot)", None),
     ]),

    # ── API Tests: Pechkin API ─────────────────────────────────────────
    ("TC-API-07", "API: Pechkin execute все методы",
     "Проверить что HTTP прокси выполняет все 7 методов корректно",
     "Pechkin API", "critical", [
         ("POST /api/v1/pechkin/execute {method: GET, url: httpbin.org/get} → 200", "status_code=200, duration>0", None),
         ("POST execute {method: POST, url: httpbin.org/post, body: {...}} → 200", "status_code=200", None),
         ("PUT, PATCH, DELETE → все 200", "Все методы проксируются", None),
         ("HEAD → status_code=200, пустое тело", "HEAD запрос работает", None),
         ("Невалидный URL → error в ответе, не 500", "error поле заполнено", None),
     ]),
    ("TC-API-08", "API: Pechkin Variables upsert",
     "Проверить создание и обновление переменных коллекции",
     "Pechkin API", "high", [
         ("PUT /api/v1/pechkin/collections/{id}/variables {scope, name, value} → 200 (не 500!)", "Переменная создана", None),
         ("GET /api/v1/pechkin/collections/{id}/variables → переменная в списке", "name и value корректны", None),
         ("Повторный PUT с тем же name → upsert", "Значение обновлено", None),
         ("DELETE /api/v1/pechkin/variables/{id} → 200", "Переменная удалена из списка", None),
     ]),
]

def create_testcases():
    print("\n[9] TEST CASES...")
    created = 0
    for tc_id, title, desc, folder, priority, steps_raw in TESTCASES_DATA:
        folder_id = TC_FOLDERS.get(folder)
        steps = make_steps(*steps_raw) if steps_raw else []
        r = c.post(TESTCASES_URL, json={
            "title": title,
            "description": desc,
            "folder_id": folder_id,
            "priority": priority,
            "status": "Ready",
            "automation_status": "automated" if "API" in tc_id else "manual",
            "project_id": c.project_id,
            "steps": steps,
            "tags": [tc_id.lower()],
        })
        if ok(r, tc_id):
            created += 1
    print(f"  [DONE] {created} test cases created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: ARTICLE FOLDERS
# ═══════════════════════════════════════════════════════════════════════════

ART_FOLDERS = {}

def create_article_folders():
    print("\n[10] ARTICLE FOLDERS...")
    structure = {
        "Architecture": [],
        "User Guides": ["Issues & Sprints", "Articles Module", "QA Module", "Generator & Pechkin"],
        "API Reference": ["Authentication API", "Tasks API", "Articles API"],
        "QA Strategy & Testing": [],
    }
    for parent_name, children in structure.items():
        r = c.post(ART_FOLDERS_URL, json={"name": parent_name})
        d = ok(r, f"art_folder {parent_name}")
        if not d:
            continue
        ART_FOLDERS[parent_name] = d.get("id", "")
        for child_name in children:
            r2 = c.post(ART_FOLDERS_URL, json={
                "name": child_name,
                "parent_id": ART_FOLDERS[parent_name]
            })
            d2 = ok(r2, f"art_folder {child_name}")
            if d2:
                ART_FOLDERS[child_name] = d2.get("id", "")
    print(f"  [DONE] {len(ART_FOLDERS)} article folders created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11: ARTICLES (14) — содержательные статьи
# ═══════════════════════════════════════════════════════════════════════════

ARTICLES_DATA = [
    # ── Architecture ─────────────────────────────────────────────────────
    ("Архитектура ErrorLens", "Architecture", "published", "architecture-overview", grid_content(
        heading(1, "Архитектура ErrorLens"),
        paragraph("ErrorLens — AI-powered QA платформа с микросервисной архитектурой. "
                  "Backend реализован на FastAPI, frontend на Vue 3, хранилище — PostgreSQL 16."),
        heading(2, "Технологический стек"),
        bullet_list(
            "Backend: FastAPI (Python 3.11), SQLAlchemy async, Alembic",
            "Frontend: Vue 3 (Composition API), Pinia, TipTap, Chart.js",
            "Хранилище: PostgreSQL 16, Redis (Streams + Cache), MinIO (S3)",
            "Инфраструктура: Docker Compose, Nginx, GitHub Actions, Prometheus + Grafana",
        ),
        heading(2, "Схема взаимодействия"),
        paragraph("Запросы от клиента проходят через Nginx → FastAPI → PostgreSQL/Redis. "
                  "Nginx проксирует /api/* на бэкенд, стрипая /api/ префикс. "
                  "WebSocket соединения идут через /ws/* для realtime обновлений."),
        heading(2, "Паттерны"),
        bullet_list(
            "Router → Service → Repository → Model (строгое разделение)",
            "HTTPException только в роутерах, бизнес-логика в сервисах",
            "Pinia stores — единственный источник состояния на фронтенде",
            "Redis Streams для event-driven автоматизации (Event Bus)",
        ),
        heading(2, "Multi-tenancy"),
        paragraph("Изоляция данных по project_id. Каждый запрос проверяет "
                  "check_project_access через JWT claim. Пользователь видит только данные своего проекта."),
    )),
    ("JWT Аутентификация", "Architecture", "published", "jwt-auth-architecture", grid_content(
        heading(1, "JWT Аутентификация и безопасность"),
        paragraph("ErrorLens использует двухтокенную схему: access_token (15 мин) + refresh_token (7 дней). "
                  "Оба хранятся в localStorage. При 401 ответе axios interceptor автоматически "
                  "делает refresh и повторяет исходный запрос."),
        heading(2, "Endpoints"),
        bullet_list(
            "POST /auth/login — получить пару токенов",
            "POST /auth/refresh — обновить access_token по refresh_token",
            "GET /auth/me — получить текущего пользователя",
            "POST /auth/logout — инвалидировать refresh_token",
        ),
        heading(2, "Middleware"),
        paragraph("require_auth dependency проверяет Authorization: Bearer {token} в каждом запросе. "
                  "При истечении токена возвращает 401 с кодом TOKEN_EXPIRED."),
        code_block(
            "# Пример использования\n"
            "@router.get('/protected')\nasync def protected_route(user: User = Depends(require_auth)):\n"
            "    return {'user': user.username}", "python"),
    )),
    ("Redis в ErrorLens", "Architecture", "published", "redis-architecture", grid_content(
        heading(1, "Redis: кэш, Streams и WebSocket"),
        paragraph("Redis используется в трёх ролях: кэш API-ответов, Event Bus через Streams, "
                  "и pub/sub для WebSocket нотификаций."),
        heading(2, "Кэш (TTL 300s)"),
        bullet_list(
            "GET /tasks/dashboard/stats — агрегированная статистика проекта",
            "GET /api/v1/qa/dashboard — QA метрики (trend, coverage, top failures)",
            "Ключ: '{endpoint}:{project_id}'. X-Cache: HIT/MISS в headers",
        ),
        heading(2, "Redis Streams (Event Bus)"),
        paragraph("Паттерн: publisher не знает о consumer. Когда задача меняет статус — "
                  "событие публикуется в stream. Consumer (automation worker) подписан и "
                  "выполняет automation rules без изменения publisher кода."),
        code_block(
            "# Публикация события\nawait publish(STREAM_TASKS, {\n"
            "    'task_id': task.id,\n    'event': 'status_changed',\n"
            "    'from': old_status,\n    'to': new_status\n})", "python"),
        heading(2, "PgBouncer"),
        paragraph("Перед PostgreSQL стоит PgBouncer (контейнер errorlens-pgbouncer-1) "
                  "в transaction mode. Максимизирует использование connection pool "
                  "при async SQLAlchemy."),
    )),

    # ── User Guides ─────────────────────────────────────────────────────
    ("Руководство: Issues и Sprint Management", "Issues & Sprints", "published", "issues-guide", grid_content(
        heading(1, "Issues и Sprint Management"),
        paragraph("Раздел Issues — полноценный трекер задач в стиле Jira. "
                  "Поддерживаются типы: Epic, Story, Task, Bug, Release. "
                  "Kanban-доска, JQL-фильтрация, спринты с burndown."),
        heading(2, "Быстрый старт"),
        bullet_list(
            "Нажмите + New Issue для создания задачи",
            "Используйте JQL Bar для фильтрации: status = 'todo' AND priority = high",
            "Перетащите карточку между колонками для смены статуса",
            "Откройте Backlog для управления рангом задач",
        ),
        heading(2, "JQL синтаксис"),
        paragraph("JQL (Jira Query Language) поддерживает операторы =, !=, IN, NOT IN, ~, IS EMPTY, "
                  "WAS, CHANGED. Функции: currentUser(), now(), startOfDay()."),
        code_block(
            "# Примеры JQL\nstatus = 'in_progress' AND assignee = currentUser()\n"
            "priority IN (high, critical) ORDER BY created DESC\n"
            "due_date < now() AND status != done", "sql"),
        heading(2, "Спринты"),
        paragraph("Создайте спринт в Backlog → + Create Sprint. Перетащите задачи из бэклога "
                  "в спринт. Нажмите Start Sprint. После завершения незакрытые задачи "
                  "переносятся в следующий спринт или бэклог."),
    )),
    ("Руководство: База знаний Articles", "Articles Module", "published", "articles-guide", grid_content(
        heading(1, "База знаний ErrorLens"),
        paragraph("Articles — Confluence-подобная база знаний с иерархией папок (max 3 уровня), "
                  "блочным редактором GridEditor, историей версий и PDF-экспортом."),
        heading(2, "Создание статьи"),
        bullet_list(
            "Нажмите + New Article для открытия fullscreen редактора",
            "Введите заголовок в поле Article title",
            "Нажмите ▼ Meta для указания Category и Tags",
            "Добавьте контент в GridEditor",
            "Нажмите Save для сохранения",
        ),
        heading(2, "GridEditor блоки"),
        bullet_list(
            "Текст с форматированием (Bold, Italic, Code)",
            "Заголовки H1-H3 (автоматически попадают в TOC)",
            "Callout-блоки: Info, Warning, Note, Success",
            "Expand-блоки (раскрываемые секции)",
            "Code блоки с подсветкой синтаксиса (highlight.js)",
        ),
        heading(2, "Импорт файлов"),
        paragraph("Поддерживается импорт .md и .docx файлов (max 5MB). "
                  "Кнопка Import в toolbar списка — создаёт новую статью. "
                  "Import from file в subheader редактора — заполняет текущую форму."),
        heading(2, "PDF Экспорт"),
        paragraph("Кнопка PDF в просмотрщике экспортирует статью через weasyprint. "
                  "PDF содержит: breadcrumbs, заголовок, дату генерации, всё содержимое "
                  "включая callout-блоки с маркерами [Info], [Warning] и т.д."),
    )),
    ("Руководство: QA Module", "QA Module", "published", "qa-guide", grid_content(
        heading(1, "QA Module — Test Management System"),
        paragraph("QA раздел — полноценная TMS в стиле TestIT: единое пространство для "
                  "тест-кейсов, тест-планов, прогонов и аналитики. Вкладки: Tree / Test Plans / Runs / Dashboard."),
        heading(2, "Тест-кейсы"),
        bullet_list(
            "Создание кейсов с шагами в формате action/expected/data",
            "Иерархия папок (max 3 уровня) для организации",
            "Bulk-операции: добавить в план, сменить статус, удалить",
            "Привязка к Issues через linked_issue_ids",
            "Экспорт в CSV",
        ),
        heading(2, "Тест-планы и прогоны"),
        paragraph("Создайте тест-план, добавьте кейсы. Нажмите Start Run — откроется экран "
                  "выполнения. Для каждого кейса отметьте результат: Passed/Failed/Blocked/Skipped. "
                  "Добавьте комментарий для упавших кейсов. Finish Run сохраняет прогон."),
        heading(2, "QA Dashboard"),
        paragraph("Trend-чарт passed/failed по последним 10 прогонам. "
                  "Distribution по статусам кейсов (pie chart). "
                  "Coverage по папкам (bar chart). "
                  "Топ-5 нестабильных кейсов. Данные кэшируются в Redis TTL 300s."),
    )),
    ("Руководство: Pechkin HTTP Client", "Generator & Pechkin", "published", "pechkin-guide", grid_content(
        heading(1, "Pechkin HTTP Client"),
        paragraph("Pechkin — встроенный HTTP-клиент в стиле Postman. "
                  "Организован в коллекции с папками и запросами. "
                  "Поддерживает все HTTP методы, auth-типы, переменные окружения."),
        heading(2, "Коллекции и запросы"),
        bullet_list(
            "Создайте коллекцию кнопкой + в панели Collections",
            "Добавьте папки и запросы внутри коллекции",
            "Импортируйте из Postman Collection v2.1 JSON (кнопка Import)",
        ),
        heading(2, "Auth типы"),
        bullet_list(
            "No Auth — запросы без авторизации",
            "Bearer Token — добавляет Authorization: Bearer {token}",
            "Basic Auth — кодирует username:password в base64",
            "API Key — добавляет в header или query parameter",
        ),
        heading(2, "Переменные"),
        paragraph("Откройте Variables Panel (gear рядом с ENV). Создайте переменные со scope: "
                  "global (доступны везде), collection (только в коллекции). "
                  "Используйте {{varName}} в URL, headers, body."),
        heading(2, "Collection Runner"),
        paragraph("Нажмите play рядом с коллекцией для запуска всех запросов. "
                  "Настройте delay между запросами, stop_on_error, количество iterations. "
                  "Результаты можно экспортировать в CSV."),
        heading(2, "Code Generation"),
        paragraph("Вкладка Code генерирует код запроса для cURL, Python (requests), "
                  "JavaScript (fetch). Кнопка Copy копирует в буфер обмена."),
    )),

    # ── API Reference ─────────────────────────────────────────────────────
    ("API: Аутентификация", "Authentication API", "published", "api-auth", grid_content(
        heading(1, "Authentication API"),
        paragraph("Все API запросы требуют Bearer токен в заголовке Authorization. "
                  "Токен получается через POST /auth/login."),
        heading(2, "POST /auth/login"),
        code_block(
            "# Request\ncurl -X POST http://192.168.1.74:3000/api/auth/login \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"username\": \"owner1\", \"password\": \"Test123!\"}'\n\n"
            "# Response 200\n{\"access_token\": \"eyJ...\", \"refresh_token\": \"eyJ...\"}", "bash"),
        heading(2, "POST /auth/refresh"),
        code_block(
            "curl -X POST http://192.168.1.74:3000/api/auth/refresh \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"refresh_token\": \"eyJ...\"}'", "bash"),
        heading(2, "Ошибки"),
        bullet_list(
            "401 — неверные credentials или истёкший токен",
            "422 — отсутствуют обязательные поля",
        ),
    )),
    ("API: Tasks (Issues)", "Tasks API", "published", "api-tasks", grid_content(
        heading(1, "Tasks API Reference"),
        paragraph("Базовый путь: /api/tasks. Все запросы требуют Bearer авторизацию."),
        heading(2, "GET /tasks"),
        paragraph("Список задач с фильтрами. Параметры: project_id, status, priority, "
                  "assignee, type_id, severity, jql, q (поиск)."),
        code_block(
            "# Пример JQL фильтрации\ncurl '/api/tasks?jql=status+%3D+todo&project_id=PID' \\\n"
            "  -H 'Authorization: Bearer TOKEN'", "bash"),
        heading(2, "POST /tasks"),
        paragraph("Создать задачу. project_id опциональный — используется default project. "
                  "Обязательное поле: title."),
        heading(2, "GET /tasks/board"),
        paragraph("Kanban-доска: возвращает {todo: [...], in_progress: [...], review: [...], done: [...]}. "
                  "Параметры: project_id, type_slug."),
        heading(2, "GET /tasks/dashboard/stats"),
        paragraph("Агрегированная статистика. Кэшируется в Redis TTL 300s. "
                  "Header X-Cache: HIT|MISS показывает источник данных."),
    )),
    ("API: Sprints", "Tasks API", "published", "api-sprints", grid_content(
        heading(1, "Sprints API Reference"),
        paragraph("Базовый путь (через nginx): /api/api/v1/sprints. "
                  "В axios вызовах — /api/v1/sprints."),
        heading(2, "Эндпоинты"),
        bullet_list(
            "GET /api/v1/sprints?project_id=... — список спринтов",
            "POST /api/v1/sprints — создать спринт",
            "POST /api/v1/sprints/{id}/start — запустить (409 если уже есть активный)",
            "POST /api/v1/sprints/{id}/complete — завершить (незакрытые → бэклог)",
            "GET /api/v1/sprints/{id}/burndown — burndown данные",
            "GET /api/v1/sprints/velocity?project_id=...&limit=5 — velocity",
        ),
        heading(2, "Ограничения"),
        bullet_list(
            "В одном проекте одновременно может быть только один активный спринт",
            "start → 409 Conflict если другой спринт уже активен",
        ),
    )),

    # ── QA Strategy & Testing ────────────────────────────────────────────
    ("QA Strategy: подход к тестированию", "QA Strategy & Testing", "published", "qa-strategy", grid_content(
        heading(1, "QA Strategy ErrorLens"),
        paragraph("ErrorLens использует многоуровневый подход к тестированию: "
                  "unit тесты в Python (pytest), API тесты (pytest + httpx), "
                  "E2E тесты (Cypress 15.7.1) против живого сервера."),
        heading(2, "Инструменты"),
        bullet_list(
            "pytest + httpx — API тесты в E:\\EL\\QA_Lens\\",
            "Cypress 15.7.1 — E2E тесты в dashboard-vue/cypress/",
            "errorlens-pytest — native плагин для отправки результатов в Launches",
            "Prometheus + Grafana — мониторинг производительности",
        ),
        heading(2, "Паттерн API тестов (QA_Lens)"),
        code_block(
            "class TestIssuesCRUD:\n"
            "    @pytest.mark.asyncio\n"
            "    async def test_create_returns_id(self, auth_client, project_id):\n"
            "        data = make_task({'project_id': project_id})\n"
            "        resp = await auth_client.post('/api/tasks', json=data)\n"
            "        assert resp.status_code == 200\n"
            "        assert 'id' in resp.json()", "python"),
        heading(2, "Паттерн Cypress тестов"),
        code_block(
            "describe('Kanban Board', () => {\n"
            "  beforeEach(() => { cy.createIssueViaApi() })\n"
            "  afterEach(() => { cy.deleteIssueViaApi('@issueId') })\n"
            "  it('shows 4 columns', () => {\n"
            "    cy.goToIssues()\n"
            "    cy.get('.kanban-board').should('exist')\n"
            "    cy.get('.kanban-column').should('have.length', 4)\n"
            "  })\n})", "javascript"),
        heading(2, "Текущие результаты (EL069)"),
        bullet_list(
            "API Tests: 86 тестов, ~80%+ pass rate после EL069 fixes",
            "Cypress E2E: 239 тестов, ~65%+ pass rate после fixes",
            "15 багов найдены в EL066-068, исправлены в EL067/EL069",
        ),
    )),
    ("EL066-069: История QA-итераций", "QA Strategy & Testing", "published", "qa-history", grid_content(
        heading(1, "История QA итераций"),
        heading(2, "EL066 — QA Pechkin (февраль 2026)"),
        paragraph("Написаны и прогнаны 181 тест (113 Cypress + 68 API). "
                  "Pass rate: 40%. Найдено 12 багов. "
                  "Critical: method selector (v-model не обновляется), variables API 500, "
                  "mode switcher click."),
        heading(2, "EL067 — Pechkin Fixes"),
        paragraph("Исправлены все 12 багов: method selector заменён на нативный select, "
                  "upsert_variable переписан через SELECT+UPDATE/INSERT, "
                  "добавлен pointer-events:none на span подсказку mode switcher."),
        heading(2, "EL068 — QA Issues & Articles (март 2026)"),
        paragraph("325 тестов (131 Cypress Issues + 108 Cypress Articles + 86 API). "
                  "Pass rate: 64.5%. Найдено 15 багов. "
                  "Critical: JQL 500, PDF 500, Sprints 404."),
        heading(2, "EL069 — Issues & Articles Fixes"),
        paragraph("Исправлены критические баги: JQL broad exception handler, "
                  "добавлены POST /sprints/{id}/start и complete, PDF try/except, "
                  "POST /tasks fallback на default_project. "
                  "Тестовые фиксы: URL mismatches (work-logs, attachments), "
                  "createIssueViaApi с project_id."),
        heading(2, "Roadmap"),
        bullet_list(
            "Интеграция errorlens-pytest декораторов @el.id() для маппинга на тест-кейсы",
            "Автоматическое обновление статуса тест-кейсов при запуске CI/CD",
            "Расширение Cypress тестов на разделы Settings и Notifications",
        ),
    )),
    ("Настройка errorlens-pytest", "QA Strategy & Testing", "published", "errorlens-pytest-setup", grid_content(
        heading(1, "errorlens-pytest — Native Reporting Plugin"),
        paragraph("errorlens-pytest v2.0 — Python пакет для автоматической отправки результатов "
                  "тестов в ErrorLens Launches. Заменяет Allure."),
        heading(2, "Установка"),
        code_block(
            "pip install -e ./errorlens-pytest\n\n"
            "# Или из git\npip install git+https://github.com/Mdyuzhev/errorlens@main#subdirectory=errorlens-pytest",
            "bash"),
        heading(2, "Конфигурация"),
        code_block(
            "# pyproject.toml\n[tool.errorlens]\nel_url = \"http://192.168.1.74:3000\"\nel_project_id = \"YOUR_PROJECT_ID\"\nel_launch_name = \"CI Run\"\n\n"
            "# Или через env переменные\nexport EL_URL=http://192.168.1.74:3000\nexport EL_TOKEN=eyJ...\nexport EL_PROJECT_ID=...",
            "bash"),
        heading(2, "Декораторы v2.0"),
        code_block(
            "import errorlens as el\n\n"
            "@el.feature('Issues')\n@el.story('Kanban Board')\n@el.severity('critical')\n"
            "@el.id('TC-ISS-01')  # маппинг на тест-кейс в QA\ndef test_kanban_board():\n"
            "    with el.step('Открыть Issues'):\n        # ...\n    with el.step('Проверить 4 колонки'):\n        # ...",
            "python"),
        heading(2, "Запуск"),
        code_block(
            "# Базовый запуск\npytest tests/ -v\n\n"
            "# Без отправки в ErrorLens\npytest tests/ --el-no-report\n\n"
            "# Verbose — шаги в консоли\npytest tests/ --el-verbose",
            "bash"),
    )),
]

def create_articles():
    print("\n[11] ARTICLES...")
    created = 0
    for title, folder, status, slug, content in ARTICLES_DATA:
        folder_id = ART_FOLDERS.get(folder)
        r = c.post(ARTICLES_URL, json={
            "title": title,
            "content": content,
            "status": status,
            "folder_id": folder_id,
            "tags": [slug],
        })
        if ok(r, f"article: {title}"):
            created += 1
    print(f"  [DONE] {created} articles created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 12: TEST PLANS (2)
# ═══════════════════════════════════════════════════════════════════════════

def create_test_plans():
    print("\n[12] TEST PLANS...")

    plans = [
        ("EL-TP-01: Regression Suite",
         "Полный регрессионный план — покрывает все основные пользовательские сценарии "
         "после каждого релиза. Включает: Auth, Issues (board/backlog/detail), "
         "Articles (editor/viewer), QA Module, Pechkin."),
        ("EL-TP-02: Pechkin Smoke",
         "Smoke-тесты HTTP клиента Pechkin. Быстрая проверка что базовые функции "
         "работают: отправка GET/POST, auth types, variables, collection runner."),
    ]

    for name, desc in plans:
        r = c.post(TEST_PLANS_URL, json={
            "name": name,
            "description": desc,
            "project_id": c.project_id,
            "status": "active",
        })
        ok(r, f"test_plan: {name}")

    print(f"  [DONE] {len(plans)} test plans created")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 13: PRINT SUMMARY + SAVE ENV
# ═══════════════════════════════════════════════════════════════════════════

def print_summary():
    print("\n" + "="*60)
    print("  ErrorLens Project Seeder — COMPLETE")
    print("="*60)
    print(f"  Project ID : {c.project_id}")
    print(f"  Epics      : {len(EPICS)}")
    print(f"  Stories    : {len(STORIES)}")
    print(f"  Bugs       : {len(BUGS)}")
    print(f"  Sprints    : {len(SPRINTS)}")
    print(f"  TC Folders : {len(TC_FOLDERS)}")
    print(f"  Test Cases : 45 (all creates attempted)")
    print(f"  Art Folders: {len(ART_FOLDERS)}")
    print(f"  Articles   : 14 (all creates attempted)")
    print(f"  Components : {len(COMPONENTS)}")
    print()
    print("  Add to your .env / pyproject.toml:")
    print(f"  EL_PROJECT_ID={c.project_id}")
    print()
    print(f"  View project: http://192.168.1.74:3000/dashboard/#/issues")
    print("="*60)

    # Сохранить project_id в файл
    if c.project_id:
        with open("/tmp/el_project_id.txt", "w") as f:
            f.write(c.project_id)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    c.login()
    cleanup()
    setup_project()
    load_task_types()
    create_components()
    create_epics()
    create_stories()
    create_bugs()
    create_sprints()
    create_tc_folders()
    create_testcases()
    create_article_folders()
    create_articles()
    create_test_plans()
    print_summary()
