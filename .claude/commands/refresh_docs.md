Обновить документацию по фактическому состоянию проекта.

## Что проверить

```bash
echo "=== Роутеры ==="
ls backend/app/routers/*.py | grep -v __init__

echo "=== Сервисы ==="
ls backend/app/services/*.py | grep -v __init__

echo "=== Модели ==="
grep 'class ' backend/app/models/db_models.py backend/app/models/user.py

echo "=== Vue Views ==="
ls dashboard-vue/src/views/*.vue 2>/dev/null

echo "=== Тесты ==="
ls backend/tests/test_*.py

echo "=== Docker ==="
cat docker/docker-compose.yml

echo "=== Зависимости ==="
cat backend/requirements.txt

echo "=== .env.example ==="
cat .env.example
```

## Что обновить

1. **`.claude/CLAUDE.md`:**
   - Секция "Текущее состояние" — волны, что реализовано
   - Секция "Структура проекта" — по фактическому дереву
   - Stack — актуальная БД, LLM провайдеры
   - Убрать устаревшие секции (Railway, SQLite если убраны)

2. **`README.md`:**
   - Инструкция по запуску (Docker Compose)
   - Список endpoint'ов
   - Переменные окружения

3. **`.env.example`** (корень и backend):
   - Все актуальные переменные
   - Комментарии что обязательно, что опционально

## Правила

- Документация на русском
- Только факты — не выдумывай функционал которого нет
- Не удаляй концептуальные секции из CLAUDE.md (архитектура, правила кода)
- Коммить: `[docs] Обновлена документация`
