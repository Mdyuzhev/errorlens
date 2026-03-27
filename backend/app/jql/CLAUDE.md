# jql/ — JQL-парсер (Jira Query Language)

## Архитектура

Lark-парсер (`grammar.lark`) → AST → SQLAlchemy WHERE-clause (`compiler.py`).
Поля описываются через `FieldDescriptor` (`fields.py`).

## Ключевые классы

- `JQLCompiler` — основной интерфейс: принимает JQL-строку, возвращает SQLAlchemy filter
- `JQLContext` — контекст компиляции (project_id и пр.)
- `FieldDescriptor` — маппинг JQL-поля на колонку БД

## FieldDescriptor

```python
@dataclass(frozen=True)
class FieldDescriptor:
    column: Any                       # SQLAlchemy column
    lookup_table: type | None = None  # связанная таблица для JOIN
    lookup_field: str | None = None   # поле для lookup (name, title)
    supports_history: bool = False    # поддержка WAS/CHANGED
    is_text_search: bool = False      # полнотекстовый поиск
    is_json: bool = False             # JSON-поле
```

## Как добавить новое JQL-поле

1. Добавить запись в `FIELD_REGISTRY` в `fields.py`:
   ```python
   "my_field": FieldDescriptor(column=Task.my_field)
   ```
2. Опционально — алиас в `FIELD_ALIASES` для Jira-совместимости
3. Поле сразу доступно через `resolve_field()`

## Поддерживаемые операторы

`=`, `!=`, `<`, `>`, `<=`, `>=`, `~` (contains), `!~`,
`IN`, `NOT IN`, `IS EMPTY`, `IS NOT EMPTY`, `WAS`, `CHANGED`.
`ORDER BY field ASC|DESC`.

## Исключения

```
JQLError (base)
├── JQLSyntaxError  — невалидный синтаксис (с позицией)
├── JQLFieldError   — неизвестное поле
├── JQLValueError   — невалидное значение
└── JQLFunctionError — неизвестная функция
```

## Запрещено

- Редактировать `grammar.lark` без проверки всех тестов JQL
- Добавлять SQL напрямую в compiler — только через FieldDescriptor
- Менять имена существующих полей в FIELD_REGISTRY (сломает сохранённые фильтры)
