# repositories/ — правила работы с репозиториями

## Принцип: чистый CRUD, никакой логики

Repository делает только: запрос к БД, eager loading relationships, возврат данных.
Бизнес-логика в Repository — запрещена.

## BaseRepository — всегда наследоваться

```python
class ArticleRepository(BaseRepository[Article]):
    def __init__(self, db: AsyncSession):
        super().__init__(Article, db)
        # Базовые методы: get_by_id, create, update, delete, count
```

`BaseRepository.get_by_id` поддерживает eager loading через `load_relations`:
```python
# base.py — автоматический selectinload по имени relationship
async def get_by_id(self, id, load_relations: list[str] | None = None):
    query = select(self.model).where(self.model.id == id)
    if load_relations:
        for relation in load_relations:
            query = query.options(selectinload(getattr(self.model, relation)))
    ...
```

## Eager loading — ОБЯЗАТЕЛЬНО для relationships

Это самый частый источник `MissingGreenlet` / `DetachedInstanceError` в проекте.
Любой метод который возвращает объект с relationships — должен загрузить их в запросе.

```python
# ✅ реальный код из task_repo.py — joinedload для 1:1, selectinload для 1:N
async def get_by_id_full(self, task_id: str) -> Task | None:
    stmt = (
        select(Task)
        .options(
            joinedload(Task.task_type),
            joinedload(Task.task_status),
            joinedload(Task.assignee_user),
            joinedload(Task.reporter),
            selectinload(Task.children),  # 1:N → selectinload
        )
        .where(Task.id == task_id)
    )
    result = await self.session.execute(stmt)
    return result.unique().scalars().first()  # unique() обязателен при joinedload

# ❌ запрещено — доступ к relationship после закрытия сессии
task = await repo.get_by_id(task_id)
comments = task.comments  # DetachedInstanceError!
```

## Паттерн для сложных запросов

Для запросов с несколькими фильтрами строить query постепенно:

```python
async def list_tasks(self, project_id, status=None, assignee_id=None) -> list[Task]:
    query = select(Task).where(Task.project_id == project_id)
    if status:
        query = query.where(Task.status_id == status)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    query = query.order_by(Task.created_at.desc())
    result = await self.session.execute(query)
    return list(result.scalars().all())
```

## При добавлении нового репозитория

Зарегистрировать в `repositories/__init__.py`. Инжектировать в соответствующий Service.

## Запрещено

- Бизнес-логика, валидация, расчёты в репозитории
- Обращение к lazy relationships вне транзакции
- Прямые SQL-строки без SQLAlchemy ORM (кроме `text()` для специфичных оптимизаций)
