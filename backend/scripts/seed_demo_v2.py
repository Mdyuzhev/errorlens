"""Seed script: 15 demo entities for JWT-authentication domain.

Usage:
    python /app/scripts/seed_demo_v2.py --project-key EL --clear
    python /app/scripts/seed_demo_v2.py --dry-run
"""

import argparse
import asyncio
import sys
import uuid
from datetime import datetime

sys.path.insert(0, "/app")

from sqlalchemy import delete, select

from app.database import async_session_maker
from app.models.article import Article
from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskType
from app.models.testcase import TestCase

from scripts.seed_content import (
    content_api_ref,
    content_architecture,
    content_refresh_token,
    content_security,
    content_troubleshoot,
    gen_id,
)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def clear_project_entities(db, project_id: str, dry_run: bool) -> None:
    """Delete TestCase -> Task -> Article for the project (FK-safe order)."""
    if dry_run:
        for name in ("TestCase", "Task", "Article"):
            print(f"  [dry-run] Would delete all {name} for project {project_id}")
        return
    await db.execute(delete(TestCase).where(TestCase.project_id == project_id))
    await db.execute(delete(Task).where(Task.project_id == project_id))
    await db.execute(delete(Article).where(Article.project_id == project_id))
    await db.flush()
    print("  Cleared existing TestCase, Task, Article.")


async def get_task_types(db, project_id: str) -> dict[str, str]:
    """Return mapping slug -> id for task types."""
    result = await db.execute(select(TaskType).where(TaskType.project_id == project_id))
    return {t.slug: t.id for t in result.scalars().all()}


async def get_status_by_slug(db, type_id: str, slug: str) -> str | None:
    result = await db.execute(
        select(TaskStatus).where(TaskStatus.task_type_id == type_id, TaskStatus.slug == slug)
    )
    s = result.scalar_one_or_none()
    return s.id if s else None


async def get_initial_status(db, type_id: str) -> str | None:
    result = await db.execute(
        select(TaskStatus).where(TaskStatus.task_type_id == type_id, TaskStatus.is_initial.is_(True))
    )
    s = result.scalar_one_or_none()
    return s.id if s else None


def _next_hid(project: Project) -> str:
    project.entity_counter += 1
    return f"{project.key}-{project.entity_counter}"


# ---------------------------------------------------------------------------
# Test case step data
# ---------------------------------------------------------------------------

TC_STEPS = [
    # TC1: Авторизация: успешный вход (6 steps)
    [
        {"action": "Открыть POST /auth/login", "expected": "Эндпоинт доступен", "data": ""},
        {"action": "Отправить email=user@test.com, password=ValidPass123", "expected": "HTTP 200",
         "data": '{"email":"user@test.com","password":"ValidPass123"}'},
        {"action": "Проверить body ответа", "expected": "Содержит access_token и token_type=bearer", "data": ""},
        {"action": "Проверить cookie", "expected": "Установлен httpOnly cookie refresh_token", "data": ""},
        {"action": "Декодировать access_token", "expected": "Payload содержит sub=user_id, exp через 30 мин",
         "data": ""},
        {"action": "Вызвать GET /auth/me с токеном", "expected": "HTTP 200, данные пользователя", "data": ""},
    ],
    # TC2: Вход со спецсимволами (4 steps)
    [
        {"action": "POST /auth/login с password=P@ss#w0rd!", "expected": "HTTP 200, вход успешен",
         "data": '{"email":"user@test.com","password":"P@ss#w0rd!"}'},
        {"action": "POST /auth/login с password=<script>alert(1)</script>",
         "expected": "HTTP 401, XSS не исполняется", "data": ""},
        {"action": "POST /auth/login с unicode эмодзи в пароле",
         "expected": "HTTP 200 или 401, без 500", "data": ""},
        {"action": "POST /auth/login с password длиной 72+ (bcrypt limit)",
         "expected": "Корректный ответ без ошибки сервера", "data": ""},
    ],
    # TC3: Ротация refresh-токена (5 steps)
    [
        {"action": "Авторизоваться, сохранить refresh_token_1", "expected": "Получен refresh_token_1", "data": ""},
        {"action": "POST /auth/refresh с refresh_token_1",
         "expected": "HTTP 200, новый access + refresh_token_2", "data": ""},
        {"action": "Проверить refresh_token_2 != refresh_token_1", "expected": "Токены различаются", "data": ""},
        {"action": "POST /auth/refresh с refresh_token_1 (старым)", "expected": "HTTP 401, инвалидирован",
         "data": ""},
        {"action": "Проверить что refresh_token_2 тоже отозван (replay detection)",
         "expected": "HTTP 401, вся token family отозвана", "data": ""},
    ],
    # TC4: Logout инвалидирует токены (5 steps)
    [
        {"action": "Авторизоваться, сохранить access и refresh", "expected": "Оба токена получены", "data": ""},
        {"action": "POST /auth/logout с Authorization header", "expected": "HTTP 200, logout", "data": ""},
        {"action": "GET /auth/me с тем же access_token", "expected": "HTTP 401", "data": ""},
        {"action": "POST /auth/refresh с тем же refresh_token", "expected": "HTTP 401", "data": ""},
        {"action": "Проверить cookie", "expected": "refresh_token удалён (expires в прошлом)", "data": ""},
    ],
    # TC5: Brute force protection (7 steps)
    [
        {"action": "4 запроса POST /auth/login с неверным паролем", "expected": "Все возвращают HTTP 401",
         "data": ""},
        {"action": "5-й запрос с неверным паролем", "expected": "HTTP 429 Too Many Requests", "data": ""},
        {"action": "Проверить заголовок Retry-After", "expected": "Присутствует, значение > 0", "data": ""},
        {"action": "Запрос с верным паролем (rate limited)", "expected": "HTTP 429", "data": ""},
        {"action": "Подождать истечения TTL rate limit", "expected": "Счётчик сброшен", "data": ""},
        {"action": "Запрос с верным паролем", "expected": "HTTP 200, вход успешен", "data": ""},
        {"action": "Проверить независимость rate limit по IP и email",
         "expected": "Другой email с того же IP — свой счётчик", "data": ""},
    ],
]


# ---------------------------------------------------------------------------
# Main seed
# ---------------------------------------------------------------------------

async def seed(project_key: str, clear: bool, dry_run: bool) -> None:
    """Create 15 demo entities: 5 Articles, 5 Issues, 5 TestCases."""
    async with async_session_maker() as db:
        result = await db.execute(select(Project).where(Project.key == project_key))
        project = result.scalar_one_or_none()
        if not project:
            print(f"Project with key '{project_key}' not found.")
            return
        print(f"Project: {project.name} (id={project.id})")

        if clear:
            print("Clearing existing entities...")
            await clear_project_entities(db, project.id, dry_run)

        type_map = await get_task_types(db, project.id)
        if not type_map:
            print("No task types found. Run project setup first.")
            return
        print(f"Task types: {list(type_map.keys())}")

        epic_tid = type_map.get("epic")
        bug_tid = type_map.get("bug")
        story_tid = type_map.get("story")
        if not all([epic_tid, bug_tid, story_tid]):
            print(f"Missing task types epic/bug/story, got: {list(type_map.keys())}")
            return

        now = datetime.utcnow()

        # --- Articles ---
        articles_meta = [
            ("Архитектура JWT-аутентификации", "Архитектура", "jwt-architecture",
             content_architecture(), "Обзор архитектуры двухтокенной JWT-аутентификации"),
            ("Руководство по безопасности API", "Безопасность", "api-security-guide",
             content_security(), "Лучшие практики защиты API-эндпоинтов"),
            ("Справочник API: Эндпоинты аутентификации", "API Reference", "auth-api-reference",
             content_api_ref(), "Описание /auth/login, /auth/refresh, /auth/logout"),
            ("Устранение ошибок авторизации", "Руководство", "auth-troubleshooting",
             content_troubleshoot(), "Диагностика ошибок 401, 403 и 500"),
            ("Refresh Token: принцип работы и ротация", "Архитектура", "refresh-token-rotation",
             content_refresh_token(), "Механизм ротации refresh-токенов"),
        ]
        art_ids = []
        for title, category, slug, content, excerpt in articles_meta:
            aid = gen_id()
            hid = _next_hid(project)
            art_ids.append(aid)
            a = Article(id=aid, human_id=hid, title=title, slug=slug, content=content,
                        excerpt=excerpt, category=category, project_id=project.id,
                        status="published", tags=["jwt", "auth"], created_at=now, published_at=now)
            if dry_run:
                print(f"  [dry-run] Article: {hid} {title}")
            else:
                db.add(a)
        art_arch, art_sec, art_api, art_trouble, art_refresh = art_ids

        # --- Issues ---
        epic_status = await get_status_by_slug(db, epic_tid, "in_progress")
        bug_status = await get_initial_status(db, bug_tid)
        story_status = await get_initial_status(db, story_tid)

        epic_id = gen_id()
        epic_hid = _next_hid(project)
        issues_data = [
            (epic_id, epic_hid, "Модуль JWT-аутентификации v2.0",
             "Полная переработка модуля аутентификации:\n"
             "- Переход на двухтокенную схему (access + refresh)\n"
             "- Ротация refresh-токенов с token family tracking\n"
             "- Rate limiting на эндпоинтах авторизации\n"
             "- Инвалидация всех сессий при смене пароля",
             "high", "in_progress", epic_tid, epic_status, None, 40.0, None,
             ["auth", "security", "v2"], None, None),
        ]
        bug1_id, bug1_hid = gen_id(), _next_hid(project)
        issues_data.append((bug1_id, bug1_hid,
            "500 при входе с паролем содержащим спецсимволы",
            "При попытке входа с паролем вида P@ss#w0rd!<>&\\ сервер возвращает 500.\n"
            "Root cause: bcrypt.hashpw() падает на null-байте внутри строки.\n"
            "Воспроизводится стабильно. Затрагивает ~2% пользователей.\n"
            "Workaround: использовать пароль без символов <>&\\",
            "critical", "todo", bug_tid, bug_status, epic_id, None, "critical",
            ["auth", "bug", "p0"], "critical", "production"))
        story1_id, story1_hid = gen_id(), _next_hid(project)
        issues_data.append((story1_id, story1_hid,
            "Реализовать ротацию refresh-токенов",
            "Реализовать механизм ротации refresh-токенов:\n"
            "- Каждый refresh выпускает новую пару токенов\n"
            "- Старый refresh инвалидируется\n"
            "- Token family tracking для обнаружения replay-атак\n"
            "- Таблица refresh_tokens: id, user_id, token_hash, family_id, is_revoked",
            "high", "todo", story_tid, story_status, epic_id, None, None,
            ["auth", "security"], None, None))
        bug2_id, bug2_hid = gen_id(), _next_hid(project)
        issues_data.append((bug2_id, bug2_hid,
            "Refresh-токен не инвалидируется при logout",
            "После POST /auth/logout refresh-токен остаётся валидным.\n"
            "Можно использовать его для получения нового access-токена.\n"
            "Ожидаемое: logout инвалидирует refresh-токен в БД.\n"
            "Причина: logout удаляет только access из Redis, не трогает refresh.",
            "high", "todo", bug_tid, bug_status, epic_id, None, "major",
            ["auth", "security", "bug"], "major", "production"))
        story2_id, story2_hid = gen_id(), _next_hid(project)
        issues_data.append((story2_id, story2_hid,
            "Rate limiting на /auth/login",
            "Добавить rate limiting на эндпоинт авторизации:\n"
            "- Max 5 попыток за 15 минут с одного IP\n"
            "- Max 10 попыток за 15 минут на один email\n"
            "- Счётчики хранить в Redis с TTL\n"
            "- Возвращать 429 Too Many Requests с Retry-After",
            "medium", "todo", story_tid, story_status, epic_id, None, None,
            ["auth", "security", "rate-limit"], None, None))

        for (tid, hid, title, desc, prio, st, type_id, status_id,
             parent, est, sev_field, labels, severity, env) in issues_data:
            t = Task(id=tid, human_id=hid, title=title, description=desc,
                     priority=prio, status=st, type_id=type_id, status_id=status_id,
                     project_id=project.id, parent_id=parent, estimated_hours=est,
                     labels=labels, created_at=now)
            if severity:
                t.severity = severity
            if env:
                t.environment = env
            if dry_run:
                print(f"  [dry-run] Issue: {hid} {title}")
            else:
                db.add(t)

        # --- TestCases ---
        tc_meta = [
            ("Авторизация: успешный вход",
             "Проверка успешного входа с валидными credentials",
             "Пользователь зарегистрирован, аккаунт активен",
             "High", "Active", "Automated", ["auth", "login", "smoke"],
             [epic_id, story1_id], [art_arch, art_api], 0),
            ("Вход с паролем со спецсимволами",
             "Проверка входа с паролем содержащим спецсимволы: !@#$%^&*()",
             "Пользователь зарегистрирован с паролем P@ss#w0rd!",
             "High", "Active", "Automated", ["auth", "login", "edge-case"],
             [bug1_id], [art_trouble], 1),
            ("Ротация refresh-токена",
             "Проверка что при refresh выпускается новая пара и старый инвалидируется",
             "Пользователь авторизован, имеет валидный refresh-токен",
             "High", "Active", "Automated", ["auth", "refresh", "security"],
             [story1_id], [art_refresh, art_arch], 2),
            ("Logout инвалидирует токены",
             "Проверка что после logout оба токена становятся невалидными",
             "Пользователь авторизован с валидными access и refresh токенами",
             "High", "Active", "Automated", ["auth", "logout", "security"],
             [bug2_id], [art_refresh, art_trouble], 3),
            ("Brute force protection",
             "Проверка rate limiting на эндпоинте авторизации",
             "Аккаунт существует, rate limit counters сброшены",
             "Medium", "Draft", "Manual", ["auth", "security", "rate-limit"],
             [story2_id], [art_sec], 4),
        ]
        for (title, desc, pre, prio, st, auto, tags,
             issue_ids, article_ids, step_idx) in tc_meta:
            tc = TestCase(
                id=gen_id(), human_id=_next_hid(project), title=title,
                description=desc, preconditions=pre, priority=prio, status=st,
                automation_status=auto, project_id=project.id, tags=tags,
                steps=TC_STEPS[step_idx],
                linked_issue_ids=issue_ids, linked_article_ids=article_ids,
                created_at=now)
            if dry_run:
                print(f"  [dry-run] TestCase: {tc.human_id} {title}")
            else:
                db.add(tc)

        if not dry_run:
            await db.commit()
            print("Seeded 15 entities (5 articles + 5 issues + 5 test cases).")
        else:
            print("[dry-run] Would seed 15 entities.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for ErrorLens")
    parser.add_argument("--project-key", default="EL", help="Project key (default: EL)")
    parser.add_argument("--clear", action="store_true", help="Delete existing entities before seeding")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be created")
    args = parser.parse_args()
    asyncio.run(seed(args.project_key, args.clear, args.dry_run))


if __name__ == "__main__":
    main()
