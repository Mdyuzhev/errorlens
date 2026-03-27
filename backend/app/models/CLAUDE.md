# models/ — правила работы с доменными моделями

## Главное правило — db_models.py запрещён

`db_models.py` — это backward-compatibility shim (`from app.models import *`).
Новые модели добавлять ТОЛЬКО в доменные файлы.

| Файл | Что хранит |
|------|-----------|
| `task.py` | Task, TaskType, TaskStatus, StatusTransition, TaskActivity, TaskComment, TaskRelation, Component, IssueCustomField, IssueCustomValue, Sprint, SprintIssue, IssueAttachment, WorkLog |
| `article.py` | Article, ArticleFolder, ArticleImage, ArticleVersion |
| `testcase.py` | TestCase, TestCaseFolder |
| `testplan.py` | TestPlan, TestPlanCase, TestPlanRun, TestPlanRunResult |
| `project.py` | Project, ProjectMember, Folder |
| `session.py` | Session, SessionData, AnalysisResult |
| `misc.py` | AutomationRule, AutomationRun, EntityLink, GitLabConnection, Notification, SavedFilter, TestRun |
| `user.py` | User |

## При добавлении новой модели — обновить ВСЕ три места

1. Создать класс в нужном доменном файле
2. Добавить import в `models/__init__.py` (секция Domain models)
3. Добавить в `__all__` список в том же файле
4. Создать Alembic-миграцию (см. `alembic/CLAUDE.md`)

## Async SQLAlchemy — критическое правило

Lazy relationship вне транзакции = `MissingGreenlet` / `DetachedInstanceError` → 500.
**Всегда** загружать relationships в запросе через `selectinload` или `joinedload`:

```python
# ✅ правильно — relationships загружены в запросе (реальный код из task_repo.py)
stmt = select(Task).options(
    joinedload(Task.task_type), joinedload(Task.task_status),
    joinedload(Task.assignee_user), selectinload(Task.children),
)

# ❌ запрещено — lazy loading вне транзакции
task = await repo.get_by_id(id)
print(task.comments)  # DetachedInstanceError
```

## Human ID

Human IDs (`EL-1`, `EL-2`…) генерируются через `await project_service.next_human_id(project_id)` с `SELECT FOR UPDATE`.
Не генерировать вручную.

## Запрещено

- Добавлять модели или изменять схему в `db_models.py`
- Пропускать регистрацию в `__init__.py`
- Изменять схему без создания Alembic-миграции
