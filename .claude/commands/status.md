Показать состояние проекта.

```bash
echo "=== Git ==="
git branch -v
git log --oneline -10
git status --short

echo "=== Backend: Роутеры ==="
ls backend/app/routers/*.py | grep -v __init__ | sort

echo "=== Backend: Сервисы ==="
ls backend/app/services/*.py | grep -v __init__ | sort

echo "=== Backend: Модели ==="
ls backend/app/models/*.py | grep -v __init__ | sort

echo "=== Frontend: Views ==="
ls dashboard-vue/src/views/*.vue 2>/dev/null | sort

echo "=== Тесты ==="
cd backend && python -m pytest tests/ -v --tb=short 2>/dev/null | tail -30
cd ..

echo "=== Docker ==="
docker compose -f docker/docker-compose.yml ps 2>/dev/null || echo "Docker не запущен"

echo "=== Задачи ==="
ls Tasks/ 2>/dev/null || echo "Нет задач"
```

Формат вывода:
```
ErrorLens — Status Report
═══════════════════════════════════
Backend:      X роутеров / X сервисов / X моделей
Frontend:     X views
Тесты:        X passed / X failed / X skipped
Docker:       running / stopped (X containers)
Ветка:        main (clean/dirty)
Коммитов:     X

Последние изменения:
- [дата] коммит...

Задачи:       X в очереди
```
