# ErrorLens — Руководство по эксплуатации сервера

Этот документ описывает полный жизненный цикл сервера ErrorLens: первоначальную настройку, штатный деплой через GitHub webhook и аварийное восстановление через Paramiko. Документ рассчитан на разработчика, который уже знаком со стеком (Docker Compose, FastAPI, PostgreSQL), но не обязательно помнит все детали конкретно этого окружения.

---

## Содержание

1. [Архитектура сервисов](#1-архитектура-сервисов)
2. [Первоначальная настройка сервера](#2-первоначальная-настройка-сервера)
3. [Переменные окружения](#3-переменные-окружения)
4. [GitHub Webhook — штатный деплой](#4-github-webhook--штатный-деплой)
5. [Миграции базы данных](#5-миграции-базы-данных)
6. [Аварийный доступ через Paramiko](#6-аварийный-доступ-через-paramiko)
7. [Rollback](#7-rollback)
8. [Диагностика и типовые сбои](#8-диагностика-и-типовые-сбои)

---

## 1. Архитектура сервисов

Весь стек запускается через единый `docker/docker-compose.yml`. Четыре сервиса, каждый со своей зоной ответственности:

| Сервис | Образ / Источник | Внешний порт | Назначение |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | Единственная БД проекта |
| `minio` | `minio/minio:latest` | 9000, 9001 | S3-хранилище для изображений статей |
| `backend` | `../backend` (build) | 8000 | FastAPI + uvicorn |
| `nginx` | `nginx/Dockerfile` (build) | **3000** | Landing + Vue Dashboard + API proxy |

Точки входа для пользователей и диагностики:

| URL | Что там |
|---|---|
| `http://<host>:3000` | Landing page |
| `http://<host>:3000/dashboard/` | Vue Dashboard |
| `http://<host>:3000/api/` | API через nginx proxy |
| `http://<host>:8000` | API напрямую (без nginx) |
| `http://<host>:8000/docs` | Swagger UI |
| `http://<host>:9001` | MinIO Console (UI) |

Nginx проксирует `/api/` → `backend:8000/` (без префикса), то есть фронтенд обращается на `/api/sessions/`, а backend видит `/sessions/`.

---

## 2. Первоначальная настройка сервера

Этот раздел выполняется **один раз** при развёртывании на новом хосте.

### 2.1 Зависимости хоста

На сервере должны быть установлены Docker Engine и Docker Compose plugin (v2). Проверка:

```bash
docker --version          # >= 24.x
docker compose version    # >= 2.x
```

Если нет — установить через официальный скрипт:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

После добавления в группу нужно перелогиниться или выполнить `newgrp docker`.

### 2.2 Клонирование репозитория

```bash
git clone https://github.com/Mdyuzhev/errorlens.git /opt/errorlens
cd /opt/errorlens
```

Путь `/opt/errorlens` — рекомендуемый. Если путь другой, учитывай это во всех командах ниже.

### 2.3 Настройка окружения

Скопировать пример и заполнить реальными значениями:

```bash
cp .env.example .env
nano .env
```

Подробнее о каждой переменной — в разделе 3.

### 2.4 Первый запуск

```bash
cd /opt/errorlens/docker
docker compose up --build -d
```

Флаг `--build` нужен при первом запуске и после любых изменений в `Dockerfile` или `requirements.txt`. В дальнейшем при штатном деплое образы пересобираются автоматически через webhook.

После старта проверь healthcheck всех сервисов:

```bash
docker compose ps
```

Все сервисы должны быть в статусе `healthy`. Если `backend` или `postgres` показывают `starting` — подожди 30–60 секунд и проверь снова. Если `unhealthy` — смотри раздел 8.

### 2.5 Применение миграций при первом запуске

Alembic запускается вручную — он не запускается автоматически при старте контейнера:

```bash
docker compose exec backend alembic upgrade head
```

---

## 3. Переменные окружения

Файл `.env` находится в корне репозитория и монтируется в контейнер `backend` через `env_file`. Файл `.env.example` содержит все ключи с безопасными заглушками.

| Переменная | Назначение | Пример |
|---|---|---|
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | `strong_password_here` |
| `MINIO_ROOT_USER` | Логин MinIO | `errorlens` |
| `MINIO_ROOT_PASSWORD` | Пароль MinIO | `strong_password_here` |
| `MINIO_ENDPOINT` | Адрес MinIO изнутри Docker сети | `minio:9000` |
| `LLM_PROVIDER` | Активный LLM-провайдер | `groq` или `gemini` |
| `GROQ_API_KEY` | API ключ Groq | `gsk_...` |
| `GEMINI_API_KEY` | API ключ Gemini (если используется) | `AIza...` |
| `ADMIN_KEY` | Мастер-ключ для admin-эндпоинтов | сложная строка |
| `ADMIN_PASSWORD` | Пароль администратора | сложная строка |
| `TESTIT_URL` | URL инсталляции TestIT (опционально) | `https://your.testit.software` |
| `TESTIT_TOKEN` | Токен TestIT (опционально) | `...` |
| `TESTIT_PROJECT_ID` | GUID проекта TestIT (опционально) | `uuid` |
| `TESTIT_ENABLED` | Включить интеграцию с TestIT | `false` / `true` |

**Важно:** `DATABASE_URL` и `MINIO_ENDPOINT` устанавливаются автоматически в `docker-compose.yml` из других переменных — не дублируй их в `.env` вручную, это вызовет конфликт.

---

## 4. GitHub Webhook — штатный деплой

### 4.1 Как это работает

GitHub отправляет POST-запрос на сервер при каждом push в ветку `main`. На сервере слушает небольшой webhook-обработчик, который при получении события выполняет `git pull` и пересобирает / перезапускает нужные контейнеры.

CI/CD pipeline в `.github/workflows/ci.yml` запускается **до** деплоя и выполняет lint (ruff, black, isort) + тесты с реальным PostgreSQL. Деплой происходит только если pipeline прошёл.

### 4.2 Настройка webhook-обработчика на сервере

Если webhook-обработчик ещё не развёрнут, нужно создать его. Простейший вариант — скрипт на Python с использованием `Flask` или `http.server`, либо утилита `webhook` (адхамара/webhook).

**Рекомендуемый подход — systemd сервис с Python-скриптом:**

Создай файл `/opt/errorlens/deploy.sh`:

```bash
#!/bin/bash
set -e

REPO_DIR="/opt/errorlens"
COMPOSE_DIR="$REPO_DIR/docker"

echo "[$(date)] Starting deploy..."

cd "$REPO_DIR"
git pull origin main

cd "$COMPOSE_DIR"
docker compose up --build -d --no-deps backend nginx

echo "[$(date)] Deploy finished."
```

Сделай скрипт исполняемым:

```bash
chmod +x /opt/errorlens/deploy.sh
```

Простейший webhook-листенер `/opt/errorlens/webhook_listener.py`:

```python
import hmac
import hashlib
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
DEPLOY_SCRIPT = "/opt/errorlens/deploy.sh"
LOG_FILE = "/var/log/errorlens_deploy.log"

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/deploy":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Проверка подписи GitHub
        signature = self.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

        # Запускаем деплой асинхронно, чтобы не блокировать ответ GitHub
        with open(LOG_FILE, "a") as log:
            subprocess.Popen(
                ["/bin/bash", DEPLOY_SCRIPT],
                stdout=log,
                stderr=log
            )

    def log_message(self, format, *args):
        pass  # Отключаем стандартный лог http.server

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9090), WebhookHandler)
    print("Webhook listener started on :9090")
    server.serve_forever()
```

Systemd unit `/etc/systemd/system/errorlens-webhook.service`:

```ini
[Unit]
Description=ErrorLens GitHub Webhook Listener
After=network.target docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/errorlens
Environment=GITHUB_WEBHOOK_SECRET=your_secret_here
ExecStart=/usr/bin/python3 /opt/errorlens/webhook_listener.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable errorlens-webhook
sudo systemctl start errorlens-webhook
sudo systemctl status errorlens-webhook
```

### 4.3 Настройка webhook в GitHub

Перейди в репозиторий → **Settings → Webhooks → Add webhook**:

| Поле | Значение |
|---|---|
| Payload URL | `http://<server-ip>:9090/deploy` |
| Content type | `application/json` |
| Secret | то же значение, что в `GITHUB_WEBHOOK_SECRET` |
| Events | `Just the push event` |
| Active | ✓ |

После сохранения GitHub сразу отправит тестовый ping — в разделе "Recent Deliveries" должен появиться ответ 200.

### 4.4 Что происходит при штатном деплое

При push в `main` полная последовательность событий такова: GitHub запускает CI pipeline → если тесты прошли, отправляет webhook → сервер делает `git pull` → пересобирает образы `backend` и `nginx` → перезапускает только эти два контейнера (postgres и minio не трогаются). Downtime минимален благодаря `--no-deps` и последовательному рестарту.

Логи деплоя пишутся в `/var/log/errorlens_deploy.log`. Смотреть в реальном времени:

```bash
tail -f /var/log/errorlens_deploy.log
```

---

## 5. Миграции базы данных

Alembic хранит версии миграций в `backend/alembic/versions/`. Каждая новая фича с изменением схемы БД обязана сопровождаться миграцией.

### Применить все новые миграции (обычно после деплоя):

```bash
cd /opt/errorlens/docker
docker compose exec backend alembic upgrade head
```

### Создать новую миграцию (делается на машине разработчика, не на сервере):

```bash
cd backend
alembic revision --autogenerate -m "add column X to table Y"
```

Сгенерированный файл нужно проверить вручную перед коммитом — autogenerate иногда пропускает сложные изменения типа переименования колонок.

### Откатить последнюю миграцию:

```bash
docker compose exec backend alembic downgrade -1
```

### Проверить текущую версию схемы:

```bash
docker compose exec backend alembic current
```

**Важно:** миграции не запускаются автоматически при старте контейнера. После каждого деплоя, содержащего изменения схемы, нужно вручную выполнить `alembic upgrade head`. Это сделано намеренно, чтобы избежать неожиданных изменений в продакшен БД.

---

## 6. Аварийный доступ через Paramiko

Когда webhook недоступен, сервер не отвечает или деплой завис — подключаемся напрямую по SSH через Paramiko. Это Python-библиотека для SSH, которая позволяет выполнять команды и передавать файлы программно.

### 6.1 Установка Paramiko

```bash
pip install paramiko
```

### 6.2 Базовый шаблон подключения

```python
import paramiko
import sys

HOST = "<server-ip>"
PORT = 22
USER = "ubuntu"           # или другой пользователь на сервере
KEY_PATH = "~/.ssh/id_rsa"  # путь к приватному ключу

def get_ssh_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=HOST,
        port=PORT,
        username=USER,
        key_filename=KEY_PATH,
    )
    return client

def run(client: paramiko.SSHClient, command: str) -> tuple[str, str]:
    """Выполнить команду, вернуть (stdout, stderr)."""
    stdin, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err

# Пример использования
if __name__ == "__main__":
    with get_ssh_client() as ssh:
        out, err = run(ssh, "docker compose -f /opt/errorlens/docker/docker-compose.yml ps")
        print(out)
        if err:
            print("STDERR:", err, file=sys.stderr)
```

### 6.3 Аварийные процедуры

**Проверить статус всех контейнеров:**

```python
out, _ = run(ssh, "docker compose -f /opt/errorlens/docker/docker-compose.yml ps")
print(out)
```

**Посмотреть последние логи backend:**

```python
out, _ = run(ssh, "docker compose -f /opt/errorlens/docker/docker-compose.yml logs --tail=100 backend")
print(out)
```

**Принудительно пересобрать и перезапустить backend:**

```python
commands = [
    "cd /opt/errorlens && git pull origin main",
    "cd /opt/errorlens/docker && docker compose up --build -d --no-deps backend nginx",
]
for cmd in commands:
    out, err = run(ssh, cmd)
    print(f"$ {cmd}\n{out}")
    if err:
        print("ERR:", err)
```

**Применить миграции в аварийном режиме:**

```python
out, err = run(ssh, "docker compose -f /opt/errorlens/docker/docker-compose.yml exec -T backend alembic upgrade head")
print(out)
```

Флаг `-T` обязателен при вызове `docker compose exec` через SSH — отключает псевдо-TTY, которого нет в неинтерактивной сессии.

**Передать файл на сервер (например, исправленный .env):**

```python
with get_ssh_client() as ssh:
    sftp = ssh.open_sftp()
    sftp.put("/local/path/.env", "/opt/errorlens/.env")
    sftp.close()
```

**Перезапустить webhook-листенер:**

```python
out, err = run(ssh, "sudo systemctl restart errorlens-webhook && sudo systemctl status errorlens-webhook")
print(out)
```

### 6.4 Безопасность SSH-подключения

Используй аутентификацию по ключу, а не по паролю. Приватный ключ храни только локально, никогда не кладёт в репозиторий. Если нужно передать ключ в CI/CD — используй зашифрованные GitHub Secrets.

---

## 7. Rollback

Rollback нужен когда деплой прошёл, но сервис упал или работает некорректно.

### 7.1 Быстрый откат кода

```bash
# На сервере (или через Paramiko)
cd /opt/errorlens

# Посмотреть последние коммиты
git log --oneline -10

# Откатиться на конкретный коммит
git checkout <commit-hash>

# Пересобрать и перезапустить
cd docker
docker compose up --build -d --no-deps backend nginx
```

После диагностики и фикса — вернуть на main:

```bash
git checkout main
git pull origin main
```

### 7.2 Откат миграции БД

Сначала откати код до версии до проблемной миграции, затем:

```bash
# Откатить одну миграцию
docker compose exec backend alembic downgrade -1

# Откатить до конкретной ревизии (ID видно в alembic current)
docker compose exec backend alembic downgrade <revision-id>
```

**Важно:** откат миграции, которая удаляла колонки или таблицы, может быть необратим если данные уже были удалены. Всегда делай `pg_dump` перед рискованными миграциями.

### 7.3 Резервная копия PostgreSQL

```bash
# Создать дамп (запускается через Paramiko или напрямую)
docker compose exec postgres pg_dump -U errorlens errorlens > /opt/backups/errorlens_$(date +%Y%m%d_%H%M%S).sql

# Восстановить из дампа
docker compose exec -T postgres psql -U errorlens errorlens < /opt/backups/errorlens_backup.sql
```

---

## 8. Диагностика и типовые сбои

### Backend не стартует (`unhealthy`)

Первым делом смотрим логи — там обычно всё написано:

```bash
docker compose logs backend --tail=50
```

Типичные причины:

1. **Не применены миграции** — в логах будет ошибка типа `column X does not exist`. Решение: `alembic upgrade head`.
2. **Неправильный `.env`** — отсутствует обязательная переменная (например, `GROQ_API_KEY` при `LLM_PROVIDER=groq`). Решение: проверить `.env` по `.env.example`.
3. **PostgreSQL ещё не готов** — backend стартовал раньше postgres. Решение: подождать, compose сам перезапустит backend благодаря `restart: unless-stopped`.

### Nginx отдаёт 502 Bad Gateway

Это значит nginx запустился, но backend недоступен. Проверь:

```bash
docker compose ps backend          # статус контейнера
docker compose logs backend --tail=20
```

### Деплой завис, старый код всё ещё работает

Webhook мог не получить события или скрипт упал. Проверь:

```bash
# Статус webhook-сервиса
sudo systemctl status errorlens-webhook

# Лог деплоя
tail -50 /var/log/errorlens_deploy.log

# В GitHub → Settings → Webhooks → Recent Deliveries
# Там видно был ли запрос и какой ответ получен
```

### PostgreSQL не стартует

```bash
docker compose logs postgres --tail=30
```

Чаще всего — проблема с правами на том `postgres_data`. Решение:

```bash
docker compose down
docker volume rm docker_postgres_data   # ВНИМАНИЕ: удалит данные!
docker compose up -d
docker compose exec backend alembic upgrade head
```

Если данные важны — сначала попробуй `docker compose exec postgres chown -R postgres:postgres /var/lib/postgresql/data`.

### MinIO недоступен, изображения не загружаются

```bash
docker compose logs minio --tail=20
docker compose restart minio
```

Если проблема в незаинициализированном бакете — перезапусти `minio-init`:

```bash
docker compose up minio-init
```

### API отвечает 404 на `/api/...`

Проверь, что nginx корректно проксирует запросы. Обрати внимание: nginx убирает префикс `/api/` при проксировании, то есть `/api/sessions/` → `backend:8000/sessions/`. Если добавлен новый роутер в backend — убедись, что он зарегистрирован в `app/main.py`.

---

*Документ актуален для архитектуры на Docker Compose. При переходе на K8s / K3s — создать отдельный DEPLOY-K8S.md.*
