Зафиксировать и залить изменения.

1. `git status`
2. `git diff --stat`
3. `cd backend && python -m pytest tests/ -v --tb=short` — если падают, СТОП, сначала чини
4. `git add -A`
5. Сформируй сообщение коммита (на русском, с префиксом)
6. `git commit -m "[prefix] сообщение"`
7. `git push origin main`

## Префиксы

`[backend]` `[frontend]` `[docker]` `[infra]` `[docs]` `[test]` `[fix]` `[refactor]`

## Правила

- НИКОГДА не пушь если тесты падают
- Один коммит = одна логическая единица
- Не коммить: node_modules/, venv/, __pycache__/, *.pyc, *.db, data/ (проверь .gitignore)
- Если изменений много — спроси нужно ли разбить на несколько коммитов
