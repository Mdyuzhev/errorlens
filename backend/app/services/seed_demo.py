"""Seed demo data for ErrorLens."""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import get_db_context
from app.models.db_models import Article, Project, ProjectMember, Task, TestCase, TestCaseFolder
from app.models.user import User

# Demo test cases - разные типы для демонстрации
DEMO_TEST_CASES = [
    {
        "title": "Авторизация: успешный вход с корректными данными",
        "description": "Проверка входа пользователя с валидными учетными данными",
        "preconditions": "Пользователь зарегистрирован в системе",
        "postconditions": "Пользователь авторизован, отображается главная страница",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Авторизация",
        "tags": ["smoke", "auth", "positive"],
        "steps": [
            {
                "step": 1,
                "action": "Открыть страницу логина",
                "expected": "Отображается форма входа",
            },
            {"step": 2, "action": "Ввести корректный email", "expected": "Email введен"},
            {"step": 3, "action": "Ввести корректный пароль", "expected": "Пароль введен"},
            {
                "step": 4,
                "action": "Нажать кнопку 'Войти'",
                "expected": "Пользователь перенаправлен на главную",
            },
        ],
    },
    {
        "title": "Авторизация: вход с неверным паролем",
        "description": "Проверка отображения ошибки при неверном пароле",
        "preconditions": "Пользователь зарегистрирован",
        "postconditions": "Отображается сообщение об ошибке",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Авторизация",
        "tags": ["auth", "negative"],
        "steps": [
            {
                "step": 1,
                "action": "Открыть страницу логина",
                "expected": "Форма входа отображается",
            },
            {"step": 2, "action": "Ввести корректный email", "expected": "Email введен"},
            {"step": 3, "action": "Ввести неверный пароль", "expected": "Пароль введен"},
            {"step": 4, "action": "Нажать 'Войти'", "expected": "Сообщение 'Неверный пароль'"},
        ],
    },
    {
        "title": "Регистрация: создание нового аккаунта",
        "description": "Проверка регистрации нового пользователя",
        "preconditions": "Email не используется в системе",
        "postconditions": "Создан новый аккаунт, отправлено письмо подтверждения",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "Регистрация",
        "tags": ["registration", "smoke", "positive"],
        "steps": [
            {"step": 1, "action": "Открыть страницу регистрации", "expected": "Форма регистрации"},
            {"step": 2, "action": "Заполнить все обязательные поля", "expected": "Поля заполнены"},
            {
                "step": 3,
                "action": "Принять пользовательское соглашение",
                "expected": "Чекбокс отмечен",
            },
            {"step": 4, "action": "Нажать 'Зарегистрироваться'", "expected": "Аккаунт создан"},
        ],
    },
    {
        "title": "API: GET /sessions возвращает список сессий",
        "description": "Проверка получения списка сессий через API",
        "preconditions": "Авторизованный запрос с JWT токеном",
        "postconditions": "Возвращен JSON со списком сессий",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "API",
        "tags": ["api", "sessions", "positive"],
        "steps": [
            {"step": 1, "action": "Отправить GET /sessions", "expected": "Status 200"},
            {"step": 2, "action": "Проверить структуру ответа", "expected": "Массив объектов"},
            {
                "step": 3,
                "action": "Проверить поля сессии",
                "expected": "id, url, created_at присутствуют",
            },
        ],
    },
    {
        "title": "API: POST /sessions создает новую сессию",
        "description": "Проверка создания сессии записи ошибок",
        "preconditions": "Валидный JWT токен",
        "postconditions": "Сессия создана в БД",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "API",
        "tags": ["api", "sessions", "positive"],
        "steps": [
            {"step": 1, "action": "POST /sessions с данными", "expected": "Status 201"},
            {"step": 2, "action": "Проверить id в ответе", "expected": "UUID формат"},
            {"step": 3, "action": "GET созданную сессию", "expected": "Данные совпадают"},
        ],
    },
    {
        "title": "UI: Дашборд отображает статистику",
        "description": "Проверка корректного отображения дашборда",
        "preconditions": "Пользователь авторизован",
        "postconditions": "Статистика отображается корректно",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "UI",
        "tags": ["ui", "dashboard", "smoke"],
        "steps": [
            {"step": 1, "action": "Открыть дашборд", "expected": "Страница загружена"},
            {"step": 2, "action": "Проверить счетчик сессий", "expected": "Число >= 0"},
            {"step": 3, "action": "Проверить график", "expected": "График отображается"},
        ],
    },
    {
        "title": "Экспорт: генерация Postman коллекции",
        "description": "Проверка экспорта сессии в Postman формат",
        "preconditions": "Сессия с записанными запросами",
        "postconditions": "Скачан .json файл Postman коллекции",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "Экспорт",
        "tags": ["export", "postman", "integration"],
        "steps": [
            {"step": 1, "action": "Открыть детали сессии", "expected": "Сессия открыта"},
            {"step": 2, "action": "Нажать 'Export Postman'", "expected": "Кнопка активна"},
            {"step": 3, "action": "Проверить скачанный файл", "expected": "Валидный JSON"},
        ],
    },
    {
        "title": "Экспорт: генерация pytest тестов",
        "description": "Проверка генерации Python тестов",
        "preconditions": "Сессия с HTTP запросами",
        "postconditions": "Скачан .py файл с тестами",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Экспорт",
        "tags": ["export", "pytest", "code-gen"],
        "steps": [
            {"step": 1, "action": "Выбрать сессию", "expected": "Сессия выбрана"},
            {"step": 2, "action": "Нажать 'Generate pytest'", "expected": "Генерация запущена"},
            {"step": 3, "action": "Скачать файл", "expected": "test_*.py файл"},
            {"step": 4, "action": "Проверить синтаксис", "expected": "Python валиден"},
        ],
    },
    {
        "title": "AI Анализ: определение severity ошибки",
        "description": "Проверка AI анализа тяжести ошибок",
        "preconditions": "Сессия с JS ошибками",
        "postconditions": "severity определен корректно",
        "priority": "Low",
        "status": "Draft",
        "automation_status": "Manual",
        "folder": "AI",
        "tags": ["ai", "analysis", "severity"],
        "steps": [
            {"step": 1, "action": "Записать сессию с ошибкой", "expected": "Ошибка записана"},
            {"step": 2, "action": "Запустить AI анализ", "expected": "Анализ выполнен"},
            {"step": 3, "action": "Проверить severity", "expected": "low/medium/high/critical"},
        ],
    },
    {
        "title": "Безопасность: XSS в поле поиска",
        "description": "Проверка защиты от XSS атак",
        "preconditions": "Авторизованный пользователь",
        "postconditions": "Скрипт не выполняется",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Security",
        "tags": ["security", "xss", "negative"],
        "steps": [
            {
                "step": 1,
                "action": "Ввести <script>alert(1)</script>",
                "expected": "Текст экранирован",
            },
            {"step": 2, "action": "Проверить DOM", "expected": "Нет script тега"},
            {"step": 3, "action": "Проверить Network", "expected": "Нет XHR с payload"},
        ],
    },
]

# Demo tasks for Kanban
DEMO_TASKS = [
    {
        "title": "Добавить OAuth авторизацию через GitHub",
        "description": "Интеграция GitHub OAuth для быстрого входа разработчиков",
        "status": "todo",
        "priority": "high",
        "labels": ["feature", "auth"],
    },
    {
        "title": "Исправить дубликаты в списке сессий",
        "description": "При быстром обновлении страницы сессии дублируются в UI",
        "status": "in_progress",
        "priority": "high",
        "labels": ["bug", "ui"],
    },
    {
        "title": "Добавить фильтрацию по дате",
        "description": "Возможность фильтровать сессии по диапазону дат",
        "status": "todo",
        "priority": "medium",
        "labels": ["feature", "ux"],
    },
    {
        "title": "Оптимизировать запросы к БД",
        "description": "Добавить индексы и пагинацию для больших объемов данных",
        "status": "done",
        "priority": "high",
        "labels": ["performance", "backend"],
    },
    {
        "title": "Написать документацию API",
        "description": "Добавить OpenAPI спецификацию и примеры использования",
        "status": "in_progress",
        "priority": "medium",
        "labels": ["docs", "api"],
    },
    {
        "title": "Добавить темную тему",
        "description": "Переключатель светлая/темная тема в настройках",
        "status": "todo",
        "priority": "low",
        "labels": ["feature", "ui"],
    },
]

# Testcase folder tree structure: {folder_name: [subfolder_names]}
DEMO_TESTCASE_FOLDERS = {
    "Авторизация": ["Позитивные", "Негативные"],
    "Регистрация": [],
    "API": ["Sessions", "TestCases"],
    "UI": [],
    "Экспорт": ["Postman", "pytest"],
    "AI": [],
    "Security": ["XSS", "CSRF"],
}

# Map: test case folder field → tree folder name
DEMO_TC_FOLDER_MAP = {
    "Авторизация": "Авторизация",
    "Регистрация": "Регистрация",
    "API": "API",
    "UI": "UI",
    "Экспорт": "Экспорт",
    "AI": "AI",
    "Security": "Security",
}

# Welcome article
WELCOME_ARTICLE = {
    "title": "Добро пожаловать в ErrorLens!",
    "slug": "welcome",
    "content": """# Добро пожаловать в ErrorLens! 🎯

ErrorLens — это инструмент для QA-инженеров, который помогает записывать и анализировать ошибки в браузере.

## Возможности

### 📹 Запись сессий
Используйте букмарклет для записи:
- JavaScript ошибок
- Console.log сообщений
- HTTP запросов и ответов
- Скриншотов страницы

### 🤖 AI Анализ
Встроенный AI анализирует записанные ошибки и выдает:
- Краткое описание проблемы
- Вероятную причину
- Рекомендации по исправлению
- Оценку критичности (severity)

### 📤 Экспорт в разные форматы
Генерируйте автотесты из записанных сессий:
- **pytest** — Python тесты
- **REST Assured** — Java тесты
- **Cypress** — E2E тесты
- **Postman** — коллекции для API
- **k6** — нагрузочные тесты

### 🔗 Интеграции
- **TestIT** — экспорт тест-кейсов
- **YouGile** — создание задач (скоро)

## Быстрый старт

1. Перейдите в **Settings** и установите букмарклет
2. Откройте тестируемый сайт
3. Нажмите букмарклет ErrorLens
4. Выберите режим записи
5. Воспроизведите баг
6. Остановите запись и отправьте на сервер

Удачного тестирования! 🚀
""",
    "excerpt": "Краткое руководство по началу работы с ErrorLens",
    "category": "Getting Started",
    "tags": ["guide", "quick-start", "tutorial"],
    "status": "published",
    "author": "ErrorLens Team",
}


async def _get_demo_project_id(db) -> str | None:
    """Get project_id for demo user's default project."""
    user_result = await db.execute(
        select(User).where(User.username == "demo")
    )
    demo_user = user_result.scalar_one_or_none()
    if not demo_user:
        return None

    project_result = await db.execute(
        select(Project).where(Project.owner_id == demo_user.id).limit(1)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        # Fallback: check membership
        member_result = await db.execute(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == demo_user.id)
            .limit(1)
        )
        project = member_result.scalar_one_or_none()

    return project.id if project else None


async def seed_demo_data():
    """Seed demo test cases, tasks, and articles."""
    async with get_db_context() as db:
        # Check if demo data already exists
        existing_cases = await db.execute(select(TestCase).limit(1))
        if existing_cases.scalar():
            print("Demo test cases already exist, skipping...")
        else:
            # Get project_id for folder creation
            project_id = await _get_demo_project_id(db)

            # Create testcase folders if project exists
            folder_map: dict[str, str] = {}  # folder_name → folder_id
            if project_id:
                existing_folders = await db.execute(
                    select(TestCaseFolder).limit(1)
                )
                if not existing_folders.scalar():
                    for folder_name, subfolders in DEMO_TESTCASE_FOLDERS.items():
                        parent = TestCaseFolder(
                            name=folder_name,
                            project_id=project_id,
                            sort_order=len(folder_map),
                        )
                        db.add(parent)
                        await db.flush()
                        folder_map[folder_name] = parent.id

                        for i, sub_name in enumerate(subfolders):
                            child = TestCaseFolder(
                                name=sub_name,
                                parent_id=parent.id,
                                project_id=project_id,
                                sort_order=i,
                            )
                            db.add(child)
                    await db.flush()
                    print(f"Added {len(DEMO_TESTCASE_FOLDERS)} testcase folders with subfolders")

            # Add test cases
            for tc_data in DEMO_TEST_CASES:
                folder_id = folder_map.get(tc_data["folder"])
                tc = TestCase(
                    title=tc_data["title"],
                    description=tc_data["description"],
                    preconditions=tc_data["preconditions"],
                    postconditions=tc_data["postconditions"],
                    priority=tc_data["priority"],
                    status=tc_data["status"],
                    automation_status=tc_data["automation_status"],
                    folder=tc_data["folder"],
                    folder_id=folder_id,
                    project_id=project_id,
                    tags=tc_data["tags"],
                    steps=tc_data["steps"],
                    created_by="demo",
                )
                db.add(tc)
            print(f"Added {len(DEMO_TEST_CASES)} demo test cases")

        # Check tasks
        existing_tasks = await db.execute(select(Task).limit(1))
        if existing_tasks.scalar():
            print("Demo tasks already exist, skipping...")
        else:
            # Add tasks
            for i, task_data in enumerate(DEMO_TASKS):
                task = Task(
                    title=task_data["title"],
                    description=task_data["description"],
                    status=task_data["status"],
                    priority=task_data["priority"],
                    labels=task_data["labels"],
                    created_at=datetime.utcnow() - timedelta(days=len(DEMO_TASKS) - i),
                )
                if task_data["status"] == "done":
                    task.completed_at = datetime.utcnow() - timedelta(days=1)
                db.add(task)
            print(f"Added {len(DEMO_TASKS)} demo tasks")

        # Check articles
        existing_articles = await db.execute(select(Article).where(Article.slug == "welcome"))
        if existing_articles.scalar():
            print("Welcome article already exists, skipping...")
        else:
            # Add welcome article
            article = Article(
                title=WELCOME_ARTICLE["title"],
                slug=WELCOME_ARTICLE["slug"],
                content=WELCOME_ARTICLE["content"],
                excerpt=WELCOME_ARTICLE["excerpt"],
                category=WELCOME_ARTICLE["category"],
                tags=WELCOME_ARTICLE["tags"],
                status=WELCOME_ARTICLE["status"],
                author=WELCOME_ARTICLE["author"],
                published_at=datetime.utcnow(),
            )
            db.add(article)
            print("Added welcome article")

        await db.commit()
        print("Demo data seeding completed!")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
