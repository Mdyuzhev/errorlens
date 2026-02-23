Управление миграциями Alembic.

## Аргументы

```
/migrate status   — текущее состояние миграций
/migrate create   — создать новую миграцию (autogenerate)
/migrate up       — применить все миграции
/migrate down     — откатить последнюю миграцию
```

## Команды

### status
```bash
cd backend
DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://errorlens:errorlens_secret@localhost:5432/errorlens}
# Для Alembic нужен sync driver
SYNC_URL=$(echo $DATABASE_URL | sed 's/asyncpg/psycopg2/g')
DATABASE_URL=$SYNC_URL alembic current
DATABASE_URL=$SYNC_URL alembic history --verbose | head -20
```

### create
Аргумент — описание миграции: `/migrate create add_generation_table`

```bash
cd backend
DATABASE_URL=postgresql://errorlens:errorlens_secret@localhost:5432/errorlens \
  alembic revision --autogenerate -m "описание"
```

После создания — проверь сгенерированный файл в `backend/alembic/versions/`.

### up
```bash
cd backend
DATABASE_URL=postgresql://errorlens:errorlens_secret@localhost:5432/errorlens \
  alembic upgrade head
```

### down
```bash
cd backend
DATABASE_URL=postgresql://errorlens:errorlens_secret@localhost:5432/errorlens \
  alembic downgrade -1
```

## Важно

- Alembic использует **sync** драйвер (psycopg2), не asyncpg
- DATABASE_URL для Alembic: `postgresql://` (не `postgresql+asyncpg://`)
- Всегда проверяй autogenerate-файл перед применением — он может пропустить изменения
- В Docker: `docker compose exec backend alembic upgrade head`
