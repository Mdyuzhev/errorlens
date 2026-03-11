# autotest-demo

Демо-проект с автотестами для интеграции GitLab CI → ErrorLens.

## Запуск локально

```bash
pip install -r requirements.txt
pytest
```

## CI/CD

Пайплайн запускается автоматически по push и по расписанию (ежедневно в 02:00 MSK).
Результаты загружаются в ErrorLens через REST API.

## Структура

- `tests/auth/` — тесты аутентификации (5 шт.)
- `tests/api/` — тесты API: users, products (9 шт.)
- `tests/ui/` — тесты поиска (3 шт.)
- `tests/integration/` — E2E checkout (3 шт.)
