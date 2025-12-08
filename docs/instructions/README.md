# Инструкции для агентов

Структура папки:

```
instructions/
├── README.md           # Этот файл
├── archive/            # Завершённые инструкции
│   ├── DONE_wave_3.2_refactoring.md
│   ├── DONE_wave_3.3_qa_infrastructure.md
│   └── DONE_wave_3.4_cicd_fix.md
└── WAVE_X.Y_*.md       # Текущие инструкции (если есть)
```

## Правила именования

- `WAVE_X.Y_name.md` — текущая инструкция
- `DONE_wave_x.y_name.md` — завершённая инструкция (в archive/)
- `REPORT_wave_x.y.md` — отчёт о выполнении (опционально)

## Workflow

1. Создать инструкцию `WAVE_X.Y_name.md`
2. Агент выполняет задачу
3. После завершения переименовать в `DONE_wave_x.y_name.md`
4. Переместить в `archive/`
