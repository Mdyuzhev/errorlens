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
| `http://192.168.1.74:3000` | Landing page |
| `http://192.168.1.74:3000/dashboard/` | Vue Dashboard |
| `http://192.168.1.74:3000/api/` | API через nginx proxy |
| `http://192.168.1.74:8000` | API напрямую (без nginx) |
| `http://192.168.1.74:8000/docs` | Swagger UI |
| `http://192.168.1.74:9001` | MinIO Console (UI) |

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

Если webhook-обработчик ещё не развёрнут, нужно создать его. Простейший вариант — скрипт на Python с использованием `http.server`.

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

Webhook-листенер `/opt/errorlens/webhook_listener.py`:

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

        # Проверка подписи GitHub — обязательно, иначе любой может триггернуть деплой
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
            subprocess.Popen(["/bin/bash", DEPLOY_SCRIPT], stdout=log, stderr=log)

    def log_message(self, format, *args):
        pass  # Отключаем стандартный лог http.server

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9091), WebhookHandler)
    print("Webhook listener started on :9091")
    server.serve_forever()
```

Systemd unit `/etc/systemd/system/errorlens-webhook.service`:

```ini
[Unit]
Description=ErrorLens GitHub Webhook Listener
After=network.target docker.service

[Service]
Type=simple
User=flomaster
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
| Payload URL | `http://192.168.1.74:9091/deploy` |
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

Когда webhook недоступен, сервер не отвечает или деплой завис — подключаемся напрямую по SSH через Paramiko.

### 6.1 Реквизиты подключения

Все данные для подключения к серверу хранятся в файле `credentials.local` в корне проекта. Этот файл не коммитится в git (есть в `.gitignore`).

```
Сервер:   192.168.1.74
Порт SSH: 22
Пользователь: flomaster
Пароль:   см. SSH_PASSWORD в credentials.local
```

**Важно для агентов:** читать кредентиалы нужно именно из `credentials.local`, а не жёстко прописывать в коде. Пример парсинга:

```python
def load_credentials(path: str = "credentials.local") -> dict:
    """Читает credentials.local и возвращает словарь KEY=VALUE."""
    creds = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                creds[key.strip()] = value.strip()
    return creds
```

### 6.2 Установка Paramiko

```bash
pip install paramiko
```

### 6.3 Подключение через пароль (основной способ для агентов)

SSH-ключ может быть недоступен в среде агента (Windows с кириллическим именем пользователя ломает путь к `.ssh`). Используй парольную аутентификацию:

```python
import paramiko

def get_ssh_client(creds: dict) -> paramiko.SSHClient:
    """Открыть SSH-сессию через пароль из credentials.local."""
    client = paramiko.SSHClient()
    # AutoAddPolicy нужен потому что агент не может нажать "yes" в интерактивном prompt
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=creds["SSH_HOST"] if "SSH_HOST" in creds else "192.168.1.74",
        port=22,
        username=creds["SSH_USER"],
        password=creds["SSH_PASSWORD"],
        timeout=15,
    )
    return client

def run(client: paramiko.SSHClient, command: str) -> tuple[str, str]:
    """Выполнить команду, вернуть (stdout, stderr). Всегда читаем оба потока."""
    _, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err
```

Полный шаблон для аварийной сессии:

```python
creds = load_credentials("credentials.local")

with get_ssh_client(creds) as ssh:
    out, err = run(ssh, "echo 'Connected OK' && docker --version")
    print(out)
    if err:
        print("STDERR:", err)
```

### 6.4 Аварийные процедуры

Все команды ниже выполняются внутри `with get_ssh_client(creds) as ssh:`.

**Проверить статус всех контейнеров:**

```python
out, _ = run(ssh, "cd /opt/errorlens/docker && docker compose ps")
print(out)
```

**Посмотреть последние логи backend:**

```python
out, _ = run(ssh, "cd /opt/errorlens/docker && docker compose logs --tail=100 backend")
print(out)
```

**Принудительно пересобрать и перезапустить (только backend и nginx, БД не трогать):**

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

**Применить миграции:**

```python
# Флаг -T обязателен через SSH — отключает псевдо-TTY, которого нет в неинтерактивной сессии
out, err = run(ssh, "cd /opt/errorlens/docker && docker compose exec -T backend alembic upgrade head")
print(out)
if err:
    print("ERR:", err)
```

**Передать файл на сервер (например, обновлённый .env):**

```python
with get_ssh_client(creds) as ssh:
    sftp = ssh.open_sftp()
    sftp.put("local/path/.env", "/opt/errorlens/.env")
    sftp.close()
    # Перезапустить backend чтобы он подхватил новый .env
    run(ssh, "cd /opt/errorlens/docker && docker compose restart backend")
```

**Перезапустить webhook-листенер:**

```python
out, err = run(ssh, "sudo systemctl restart errorlens-webhook && sudo systemctl status errorlens-webhook --no-pager")
print(out)
```

**Полный рестарт стека (крайняя мера — будет downtime):**

```python
commands = [
    "cd /opt/errorlens/docker && docker compose down",
    "cd /opt/errorlens/docker && docker compose up --build -d",
    "cd /opt/errorlens/docker && docker compose exec -T backend alembic upgrade head",
]
for cmd in commands:
    out, err = run(ssh, cmd)
    print(f"$ {cmd}\n{out or err}")
```

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
# Создать дамп
docker compose exec postgres pg_dump -U errorlens errorlens > /opt/backups/errorlens_$(date +%Y%m%d_%H%M%S).sql

# Восстановить из дампа
docker compose exec -T postgres psql -U errorlens errorlens < /opt/backups/errorlens_backup.sql
```

Через Paramiko:

```python
run(ssh, "mkdir -p /opt/backups")
out, err = run(ssh, "cd /opt/errorlens/docker && docker compose exec -T postgres pg_dump -U errorlens errorlens > /opt/backups/errorlens_$(date +%Y%m%d_%H%M%S).sql")
print(out or err)
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
docker compose ps backend
docker compose logs backend --tail=20
```

### Деплой завис, старый код всё ещё работает

Webhook мог не получить событие или скрипт упал. Проверь:

```bash
sudo systemctl status errorlens-webhook
tail -50 /var/log/errorlens_deploy.log
```

Также проверь в GitHub → Settings → Webhooks → Recent Deliveries — там видно был ли запрос и какой ответ получен.

### PostgreSQL не стартует

```bash
docker compose logs postgres --tail=30
```

Чаще всего — проблема с правами на томе `postgres_data`. Решение:

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

Nginx убирает префикс `/api/` при проксировании, то есть `/api/sessions/` → `backend:8000/sessions/`. Если добавлен новый роутер в backend — убедись, что он зарегистрирован в `app/main.py`.

---

*Документ актуален для архитектуры на Docker Compose. При переходе на K8s / K3s — создать отдельный DEPLOY-K8S.md.*
