Ревью кода: стиль, архитектура, тесты.

1. Посмотри что изменилось: `git diff --name-only HEAD~5`
2. Для каждого файла проверь:

## Стиль (Python)
- PEP8, type hints на всех функциях
- Async для всех I/O операций
- Файл ≤ 500 строк
- Нет `import *`, нет bare `except:`
- Specific exceptions only

## Архитектура
- Router → Service → Repository → Model (не нарушать)
- Router не содержит бизнес-логику
- Service не импортирует Router
- Нет прямого SQL в роутерах
- WebSocket state — Redis/DB, не in-memory

## Frontend (Vue)
- Компоненты < 300 строк
- Store (Pinia) для состояния, не props drilling
- API вызовы через `services/api.js`, не напрямую

## Тесты
- Каждый сервис имеет тест
- test_empty_input, test_none_handling, test_error_recovery
- Тесты проходят: `cd backend && python -m pytest tests/ -v --tb=short`

## Безопасность
- Нет хардкода секретов и паролей
- Нет API ключей в коде
- .gitignore актуален
- .env файлы в .gitignore

Формат:
```
ErrorLens — Code Review
═══════════════════════════
Файлов проверено: X

✅ services/generation.py — OK
⚠️ routers/sessions.py — бизнес-логика в роутере, вынести в сервис
❌ config.py — API ключ захардкожен

Итого: X ✅ / X ⚠️ / X ❌
```
