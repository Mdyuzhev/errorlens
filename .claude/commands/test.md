Запуск тестов.

```bash
cd backend
python -m pytest tests/ -v --tb=long
```

Если есть падения:
- Покажи какой тест упал и почему
- Предложи исправление
- Спроси нужно ли чинить сейчас

Покрытие (если pytest-cov установлен):
```bash
cd backend
python -m pytest tests/ --cov=app --cov-report=term-missing 2>/dev/null
```

Формат:
```
ErrorLens — Тесты
═══════════════════
✅ X passed
❌ X failed
⏭️ X skipped

Покрытие: X%

Непокрытые области:
- app/services/... (строки X-Y)
```
