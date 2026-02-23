Управление Docker окружением.

## Аргументы

```
/docker up      — собрать и запустить
/docker down    — остановить
/docker logs    — показать логи
/docker rebuild — пересобрать с нуля
/docker ps      — статус контейнеров
```

## Команды

### up (по умолчанию если без аргумента)
```bash
cd docker
docker compose up --build -d
echo "Ожидаю запуск..."
sleep 10
docker compose ps
curl -s http://localhost:8000/health || echo "Backend не отвечает"
curl -s http://localhost:3000/api/health || echo "Nginx не отвечает"
```

### down
```bash
cd docker
docker compose down
```

### logs
```bash
cd docker
docker compose logs --tail=50 -f
```

Если нужен конкретный сервис: `docker compose logs backend --tail=100`

### rebuild
```bash
cd docker
docker compose down
docker compose build --no-cache
docker compose up -d
sleep 15
docker compose ps
curl -s http://localhost:8000/health
```

### ps
```bash
cd docker
docker compose ps
echo ""
echo "=== Health ==="
curl -s http://localhost:8000/health 2>/dev/null || echo "Backend: DOWN"
curl -s http://localhost:3000/api/health 2>/dev/null || echo "Nginx proxy: DOWN"
curl -s http://localhost:3000/ 2>/dev/null | head -5 || echo "Landing: DOWN"
```

## Формат вывода

```
ErrorLens — Docker
════════════════════
postgres:  ✅ healthy (port 5432)
backend:   ✅ healthy (port 8000)
nginx:     ✅ running (port 3000)

URLs:
  Landing:    http://localhost:3000
  Dashboard:  http://localhost:3000/dashboard/
  API:        http://localhost:3000/api/
  Swagger:    http://localhost:8000/docs
```

## Если backend не стартует

1. `docker compose logs backend --tail=50` — посмотри ошибку
2. Частые проблемы:
   - `DATABASE_URL not set` → проверь docker-compose.yml environment
   - `connection refused postgres` → postgres ещё не ready, увеличь depends_on timeout
   - `ModuleNotFoundError` → requirements.txt не синхронизирован
