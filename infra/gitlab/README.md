# Local GitLab CE for CI Testing

Локальный GitLab Community Edition для тестирования интеграции ErrorLens с CI/CD пайплайнами.

## Требования

- Docker и Docker Compose
- Минимум 4 CPU, 6 GB свободной RAM
- Первый запуск занимает 3–5 минут (инициализация GitLab)

## Quickstart

```bash
# 1. Запустить GitLab и Runner
docker compose up -d

# 2. Дождаться готовности (3-5 минут)
# Проверить статус:
docker compose ps
curl -sf http://localhost:8080/-/health

# 3. Выполнить первоначальную настройку
chmod +x setup.sh
./setup.sh

# 4. Открыть GitLab
# http://localhost:8080
# Login: root / ErrorLens2024!

# 5. Указать ERRORLENS_TOKEN в .env (после создания токена в ErrorLens)
```

## Что делает setup.sh

1. Ожидает готовности GitLab (healthcheck, до 10 минут)
2. Создаёт Personal Access Token через Rails runner
3. Создаёт группу `qa-team`
4. Создаёт проект `autotest-demo` в группе
5. Регистрирует GitLab Runner с Docker executor
6. Создаёт CI/CD переменные `ERRORLENS_URL` и `ERRORLENS_TOKEN` на уровне группы

## Остановка

```bash
# Остановить, сохранив данные
./teardown.sh

# Остановить и удалить все данные
./teardown.sh --purge
```

## Troubleshooting

### GitLab долго стартует
Это нормально. Первый запуск — 3–5 минут, последующие — 1–2 минуты.
Следить за прогрессом: `docker logs -f errorlens-gitlab`

### Как смотреть логи
```bash
docker logs errorlens-gitlab
docker logs errorlens-gitlab-runner
```

### Сбросить пароль root
```bash
docker exec -it errorlens-gitlab gitlab-rake "gitlab:password:reset[root]"
```

### Runner не регистрируется
- Проверить что GitLab полностью запущен: `curl http://localhost:8080/-/health`
- Проверить сеть: runner должен видеть gitlab по имени `gitlab` через docker network
- Логи runner: `docker logs errorlens-gitlab-runner`
