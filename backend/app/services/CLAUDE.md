# services/ — правила работы с сервисным слоем

## Принцип: вся бизнес-логика живёт здесь

Service получает Repository (или создаёт сам), выполняет логику, публикует события.
Прямых SQL-запросов нет — только вызовы Repository-методов.

## Создание сервиса — шаблон

```python
class ArticleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ArticleRepository(db)  # Repository инжектируется

    async def create_article(self, title: str, project_id: str, ...) -> Article:
        # Бизнес-валидация
        # Создание через repo
        article = await self.repo.create({...})
        # Публикация события
        await publish("article.created", {...})
        return article
```

## EventPublisher — публикация событий в Redis Streams

```python
from app.services.event_publisher import publish

# Шина: el:events, два consumer group: notifications и automations
# publish() — module-level async function, НЕ метод класса
await publish("task.status_changed", {
    "task_id": task.id, "project_id": project_id,
    "old_status": old, "new_status": new
}, actor_id=user.id, project_id=project_id)
# publish() НЕ бросает исключений — Redis down не ломает основной поток
```

## Human ID — генерация через проект

```python
# Атомарный инкремент с SELECT FOR UPDATE (метод ProjectService)
# Сигнатура: async def next_human_id(self, project_id: str) -> str | None
human_id = await project_service.next_human_id(project_id)  # → "EL-42"
```

## CacheService — кэширование запросов

Для дорогих агрегаций использовать `CacheService` с TTL.
Не хранить состояние в памяти сервиса для distributed-сценариев.

## Запрещено

- Прямые SQLAlchemy-запросы (select/insert/update) в сервисе — только через Repository
- In-memory state для данных которые нужны в нескольких контейнерах
- Бизнес-логика в роутерах — её место здесь
- Bare `except:` — только конкретные типы исключений
