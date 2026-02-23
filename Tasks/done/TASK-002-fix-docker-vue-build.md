# TASK: Исправить Docker-сборку — Vue билд и настройка путей

## Цель

Сделать `docker compose up --build` полностью автономным — без ручных шагов на хосте. Сейчас nginx/Dockerfile копирует pre-built `dist/` с хоста, что требует ручного `npm run build` и не выставляет правильные env-переменные при сборке.

## Контекст

Агент убрал multi-stage build из `nginx/Dockerfile` потому что `npm ci` падал с сетевой ошибкой внутри Docker. Это корневая причина, и её нужно решить, а не обходить.

---

## Часть 1: Вернуть multi-stage build в nginx/Dockerfile

### Файл: `nginx/Dockerfile`

Текущее состояние (КОСТЫЛЬ — убрать):
```dockerfile
FROM nginx:alpine
COPY dashboard-vue/dist /usr/share/nginx/html/dashboard-vue/dist/
```

Требуемое состояние — multi-stage build:

| Stage | Base image | Назначение |
|-------|-----------|------------|
| frontend-builder | node:20-alpine | npm ci + npm run build |
| final | nginx:alpine | копирует dist из stage 1 + static files |

Требования к Stage 1 (frontend-builder):
- WORKDIR `/build`
- Копировать `dashboard-vue/package.json` и `dashboard-vue/package-lock.json` отдельно (кэш слоёв)
- `npm ci --prefer-offline` (для надёжности)
- Копировать остальные файлы `dashboard-vue/`
- ENV при сборке: `VITE_BASE=/dashboard/` и `VITE_API_URL=/api`
- `npm run build`

Требования к Stage 2 (final):
- Копировать `nginx/nginx.conf` → `/etc/nginx/conf.d/default.conf`
- Копировать `landing/` → `/usr/share/nginx/html/`
- Копировать `bookmarklet/recorder.js` и `bookmarklet/recorder.min.js` → `/usr/share/nginx/html/bookmarklet/`
- `COPY --from=frontend-builder /build/dist /usr/share/nginx/html/dashboard-vue/dist/`

### Если npm ci всё ещё падает с сетевой ошибкой

Причины и решения:

| Причина | Решение |
|---------|---------|
| DNS внутри Docker не резолвит registry.npmjs.org | Добавить в `docker-compose.yml` у nginx: `dns: ["8.8.8.8", "8.8.4.4"]` или `network_mode: host` при build |
| Корпоративный прокси/VPN блокирует | Попробовать `npm ci --registry https://registry.npmmirror.com` |
| Таймаут на медленном соединении | `npm ci --fetch-timeout=120000` |

Если ни одно решение не работает — fallback подход с отдельным build-контейнером:

### Альтернатива: отдельный сервис в docker-compose для сборки Vue

```yaml
  frontend-builder:
    image: node:20-alpine
    working_dir: /build
    volumes:
      - ../dashboard-vue:/build
      - vue_dist:/build/dist
    environment:
      VITE_BASE: /dashboard/
      VITE_API_URL: /api
    command: sh -c "npm ci && npm run build"
    # Сервис запускается один раз, потом останавливается

  nginx:
    # ...
    volumes:
      - vue_dist:/usr/share/nginx/html/dashboard-vue/dist:ro
    depends_on:
      frontend-builder:
        condition: service_completed_successfully
```

Этот вариант использовать ТОЛЬКО если multi-stage build невозможен из-за сетевых ограничений.

---

## Часть 2: Исправить docker/Dockerfile (full-stack)

### Файл: `docker/Dockerfile`

Тот же multi-stage build, но с правильными env для single-container режима (FastAPI раздаёт Vue на `/`):

Stage 1 ENV:
- `VITE_BASE=/` (Vue на корне, FastAPI раздаёт)
- `VITE_API_URL=` (пустой — запросы идут на тот же хост)

Остальное аналогично nginx/Dockerfile stage 1.

---

## Часть 3: Проверить что VITE_BASE работает в vite.config.js

### Файл: `dashboard-vue/vite.config.js`

Текущее состояние (✅ уже правильно):
```javascript
base: process.env.VITE_BASE || '/',
```

Проверить:
- `VITE_BASE=/dashboard/` → `npm run build` → в `dist/index.html` все пути ассетов начинаются с `/dashboard/`
- `VITE_BASE=/` → пути начинаются с `/`

---

## Часть 4: Проверить что Vue Router и API client работают с /dashboard/ base

### Файл: `dashboard-vue/src/router/index.js`

Текущее: `createWebHashHistory()` — hash-роутинг (`/dashboard/#/login`). С `VITE_BASE` проблем не будет, hash mode не зависит от base path.

✅ Не требует изменений.

### Файл: `dashboard-vue/src/services/api.js`

Текущее:
```javascript
const API_URL = import.meta.env.VITE_API_URL || ''
```

При сборке с `VITE_API_URL=/api`:
- Все запросы пойдут на `/api/auth/login`, `/api/sessions` и т.д.
- Nginx проксирует `/api/` → backend:8000/

✅ Не требует изменений, но проверить что при `VITE_API_URL=/api` запросы не дублируют prefix.

Тест: `api.post('/auth/login')` → должен уходить на `/api/auth/login`, NOT `/api//auth/login`.
Проверить что `baseURL: '/api'` + `api.post('/auth/login')` → корректный URL. Axios склеивает: `baseURL + path` → `/api` + `/auth/login` = `/api/auth/login` ✅

---

## Часть 5: .dockerignore — НЕ исключать dashboard-vue/dist

### Файл: `.dockerignore`

Если multi-stage build работает, `dist/` в .dockerignore не нужен, потому что dist собирается ВНУТРИ Docker.

Проверить что `.dockerignore` содержит:
```
dashboard-vue/node_modules
```

НО НЕ содержит:
```
dashboard-vue/dist
```

(dist не нужен в контексте, но и не мешает — multi-stage его не использует)

---

## Запрещено

- Оставлять копирование pre-built `dist/` с хоста как основной подход
- Хардкодить `base: '/dashboard/'` в vite.config.js (должен браться из env)
- Менять nginx.conf routing
- Менять backend код

---

## Критерии готовности

| Проверка | Команда / условие |
|----------|-------------------|
| Чистая сборка | `docker compose down -v && docker compose up --build` — все сервисы healthy |
| Без ручных шагов | Удалить `dashboard-vue/dist/`, запустить `docker compose up --build` — dashboard работает |
| Landing page | `curl http://localhost:3000` → HTML страница |
| Dashboard | `http://localhost:3000/dashboard/` → Vue app загружается (CSS/JS без 404) |
| Dashboard ассеты | Открыть DevTools → Network → нет 404 ошибок на JS/CSS |
| API через dashboard | Залогиниться demo/ErrorLenseTest → сессии отображаются |
| API через curl | `curl http://localhost:3000/api/health` → `{"status":"ok"}` |
| Backend напрямую | `curl http://localhost:8000/health` → `{"status":"ok"}` |
| Full-stack Dockerfile | `docker build -f docker/Dockerfile .` — собирается без ошибок |

---

## Диагностика если npm ci падает

Выполни внутри Docker вручную для диагностики:

```bash
docker run --rm -it node:20-alpine sh -c "ping -c 3 registry.npmjs.org && npm config get registry"
```

Если ping не проходит — проблема DNS/сети Docker. Решения:

1. `docker-compose.yml` → добавить DNS:
```yaml
services:
  nginx:
    dns:
      - 8.8.8.8
      - 8.8.4.4
```

2. Docker Desktop → Settings → Docker Engine → добавить:
```json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

3. Если VPN — попробовать собрать с `--network=host`:
```bash
docker compose build --build-arg BUILDKIT_SANDBOX_HOSTNAME=host nginx
```

Записать причину и решение в этот файл задачи перед закрытием.

---

## Время: 30 мин — 1 час
