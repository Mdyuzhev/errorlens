# routers/ — правила работы с роутерами FastAPI

## Принцип: роутер = тонкий контроллер

Роутер делает ТОЛЬКО: валидацию входа, вызов сервиса, возврат ответа.
Бизнес-логика в роутере — запрещена. Прямые SQL-запросы — запрещены.

```python
# ✅ правильно — тонкий контроллер
@router.post("")
async def create_task(data: TaskCreate, db=Depends(get_db), user=Depends(require_auth)):
    service = TaskService(db)
    task = await service.create_task(data.title, user_id=user.id, **data.model_dump())
    return {"id": task.id, "message": "Task created"}

# ❌ запрещено — бизнес-логика в роутере
@router.post("")
async def create_task(data: TaskCreate, db=Depends(get_db)):
    task = Task(**data.model_dump())  # прямое создание модели
    db.add(task)
    await db.commit()
    return task
```

## Multi-tenancy — обязательно

Все новые эндпоинты должны фильтровать данные по `project_id` через `check_project_access`.
Эндпоинт без проверки проекта — это дыра в изоляции между тенантами.

## Pydantic-схемы

Схемы запроса/ответа (`Create`, `Update`, `Response`) описывать прямо в файле роутера.
Исключение: если схемы используются более чем в одном роутере — выносить в `schemas/`.

## Роутеры (регистрация в main.py)

35 роутеров зарегистрированы в `main.py`. При добавлении нового — не забыть
импортировать и зарегистрировать там же. Nginx проксирует `/api/` → backend `/`.

### Публичные эндпоинты (без auth) — явные исключения

| Роутер | Эндпоинты | Причина |
|--------|-----------|---------|
| `auth.py` | `/login`, `/refresh` | Авторизация |
| `generation.py` | `/from-swagger`, `/result/{id}`, `/download/{id}`, `/health` | Внешние интеграции |
| `analysis.py` | `/analyze` | Bookmarklet |

### Роутеры без multi-tenancy — корректные исключения

`admin.py` (require_admin), `notifications.py` (user-scoped), `auth.py`,
`entity_links.py`, `exports.py`, `integrations.py`.

## Запрещено

- Бизнес-логика, расчёты, решения в роутере
- Прямое обращение к `db` без Repository/Service
- Эндпоинты без auth (`require_auth`) кроме явно публичных
- Эндпоинты без multi-tenancy проверки для project-scoped данных
