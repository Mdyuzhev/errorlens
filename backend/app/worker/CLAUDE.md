# worker/ — фоновые обработчики событий

## Архитектура

Три независимых процесса, каждый — Redis Streams consumer с отдельной consumer group.

| Worker | Stream | Consumer Group | Назначение |
|--------|--------|---------------|------------|
| `generator_worker.py` | `STREAM_GENERATION` | `generators` | Генерация тестов (LLM) |
| `notification_worker.py` | `el:events` | `notifications` | Создание уведомлений |
| `automation_worker.py` | `el:events` | `automations` | Выполнение правил автоматизации |

## Ключевые паттерны

**Consumer ID** — `{prefix}-{uuid[:8]}` для горизонтального масштабирования.

**Идемпотентность** — notification_worker использует `ON CONFLICT DO NOTHING`.
automation_worker фильтрует по `task.status_changed` и матчит правила.

**БД в workers** — каждый event обрабатывается в отдельной async DB session.
Не переиспользовать session между событиями.

**Generator** — результат публикуется через Redis Pub/Sub (`el:ws:{task_id}`)
для push-уведомления на фронтенд.

## Как добавить новый worker

1. Создать `backend/app/worker/my_worker.py`
2. Определить consumer group и stream
3. Добавить сервис в `docker/docker-compose.yml`
4. Паттерн: бесконечный цикл `XREADGROUP` → обработка → `XACK`

## Запрещено

- Общее состояние между обработками событий (stateless per event)
- Блокирующие синхронные вызовы (всё async)
- Пропуск XACK после обработки (событие зависнет в pending)
