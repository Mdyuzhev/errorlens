Актуализируй контекст перед началом работы.

1. Прочитай `.claude/CLAUDE.md` — основной контекст проекта
2. Прочитай `README.md`
3. Структура проекта: `find . -type f -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*.pyc' | head -80`
4. Git: `git status && git log --oneline -5`
5. Backend роутеры: `ls backend/app/routers/`
6. Backend сервисы: `ls backend/app/services/`
7. Backend модели: `ls backend/app/models/`
8. Тесты: `cd backend && python -m pytest tests/ -v --tb=short 2>/dev/null | tail -20`
9. Docker: `docker compose -f docker/docker-compose.yml ps 2>/dev/null || echo "Docker не запущен"`
10. Задачи: `ls Tasks/ 2>/dev/null || echo "Нет задач"`

Выведи краткий отчёт:
```
ErrorLens — статус проекта
═══════════════════════════
Backend:       X роутеров, X сервисов
Frontend:      Vue 3 + Vite
Тесты:         X passed / X failed
Docker:        running / stopped
Ветка:         main
Последний коммит: ...
Задач:         X
```

НЕ создавай файлы. НЕ меняй код. Только читай и отчитывайся.
