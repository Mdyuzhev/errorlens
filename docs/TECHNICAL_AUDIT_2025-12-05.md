# ErrorLens: Технический аудит

**Дата:** 2025-12-05  
**Версия:** 2.0 (полный аудит перед WAVE_3.2)  
**Аудитор:** CTO Review  
**Статус:** 🔴 Требуется рефакторинг

---

## Executive Summary

ErrorLens находится в **работоспособном состоянии** с **незавершённым рефакторингом**. Предыдущий аудит (CODE_AUDIT_REPORT.md) **устарел** — часть указанных проблем уже решена, но появились новые.

### Ключевые метрики

| Метрика | Значение | Целевое | Статус |
|---------|----------|---------|--------|
| Backend: max file LOC | 409 | <500 | ✅ OK |
| Frontend: max file LOC | 687 | <500 | ⚠️ Warning |
| Bookmarklet: legacy LOC | 2438 | 0 | 🔴 Critical |
| Routers без Service | 8/11 | 0/11 | 🔴 Critical |
| TODO/FIXME в коде | 2 | 0 | ✅ OK |
| Тестовое покрытие | ~40% | 80% | ⚠️ Warning |

### Приоритеты рефакторинга

1. **P0 Critical:** Bookmarklet — удалить legacy, использовать модульную структуру
2. **P1 High:** Backend — добавить недостающие Services и перевести роутеры
3. **P2 Medium:** Frontend — разбить крупные компоненты
4. **P3 Low:** Тесты — расширить покрытие новых сервисов

---

## 1. Backend Analysis

### 1.1 Архитектура слоёв

**Текущее состояние:**

```
Routers (11)  →  Services (5)  →  Repositories (5)  →  Models
    ↓                                                    ↑
    └──────────── 8 роутеров работают напрямую ──────────┘
```

**Детальный анализ:**

| Layer | Файлы | Статус |
|-------|-------|--------|
| **Routers** | 11 файлов | ⚠️ 8 из 11 обходят Service layer |
| **Services** | 5 файлов | ✅ Хорошая реализация |
| **Repositories** | 5 файлов | ✅ Добавлены в WAVE_3.1 |
| **Models** | 3 файла | ✅ OK |

### 1.2 Роутеры: детальный анализ

| Router | LOC | Service | Repo | Статус | Действие |
|--------|-----|---------|------|--------|----------|
| sessions.py | 195 | ✅ SessionService | ✅ | ✅ Образец | — |
| projects.py | 192 | ✅ ProjectService | ✅ | ✅ OK | — |
| auth.py | 89 | ✅ auth.py | ✅ | ✅ OK | — |
| **articles.py** | 209 | ❌ | ❌ | 🔴 | Нужен ArticleService |
| **tasks.py** | 207 | ❌ | ❌ | 🔴 | Нужен TaskService |
| **testcases.py** | 203 | ❌ | ❌ | 🔴 | Нужен TestCaseService |
| **testruns.py** | 110 | ❌ | ❌ | 🔴 | Нужен TestRunService |
| **tests.py** | 122 | ❌ | ❌ | 🔴 | Нужен TestService |
| **analysis.py** | 180 | ❌ | — | ⚠️ | Нужен AnalysisService |
| **exports.py** | 217 | Частично | — | ⚠️ | Доработать |
| **integrations.py** | 120 | ❌ | — | ⚠️ | Нужен IntegrationService |

### 1.3 Необходимые сервисы

**Создать:**
- `services/article_service.py` — CRUD для статей
- `services/task_service.py` — CRUD для задач Kanban
- `services/testcase_service.py` — CRUD + бизнес-логика тест-кейсов
- `services/testrun_service.py` — управление запусками тестов
- `services/analysis_service.py` — вынести логику анализа из analyzer.py
- `services/integration_service.py` — интеграции TestIT, webhooks

**Создать репозитории:**
- `repositories/article_repo.py`
- `repositories/task_repo.py`
- `repositories/testrun_repo.py`

### 1.4 Файлы по размеру (Python)

```
409  generators/testit.py        ✅ OK
394  generators/pytest.py        ✅ OK
372  models_pydantic.py          ✅ OK (TODO: split to schemas/)
356  services/seed_demo.py       ✅ OK
349  models/db_models.py         ✅ OK
335  generators/postman.py       ✅ OK
328  session_analyzer.py         ⚠️ Вынести в AnalysisService
328  services/project_service.py ✅ OK
323  generators/k6.py            ✅ OK
284  generators/restassured.py   ✅ OK
```

### 1.5 Hardcoded Values

| Файл | Строка | Проблема | Решение |
|------|--------|----------|---------|
| generators/base.py | 23 | `return "http://localhost"` | Использовать config |
| generators/cypress.py | 181-189 | Hardcoded localhost URLs | Параметризовать |
| bookmarklet/src/core/config.js | 35 | `LOCAL_URL` | ✅ OK (dev-only) |

---

## 2. Bookmarklet Analysis

### 2.1 Критическая проблема: дублирование

**Текущее состояние:**

```
bookmarklet/
├── recorder.js          # 2438 LOC — LEGACY, используется в production!
├── recorder.dev.js      # 1019 LOC — dev версия legacy
├── recorder.min.js      #  281 LOC — minified legacy
├── recorder.js.backup   # backup
│
└── src/                 # НОВАЯ модульная структура — НЕ ИСПОЛЬЗУЕТСЯ!
    ├── index.js         #   43 LOC — entry point
    ├── core/
    │   ├── api.js       #   73 LOC
    │   ├── config.js    #   67 LOC
    │   └── state.js     #   69 LOC
    ├── interceptors/
    │   ├── console.js   #   81 LOC
    │   ├── errors.js    #   81 LOC
    │   ├── fetch.js     #   93 LOC
    │   ├── xhr.js       #  108 LOC
    │   └── index.js     #   40 LOC
    ├── ui/
    │   ├── widget.js    #  394 LOC
    │   └── styles.js    #  265 LOC
    └── utils/
        └── helpers.js   #   75 LOC
```

**Проблема:**

Production использует `recorder.js` (2438 LOC монолит), а модульная структура `src/` создана, но **не подключена**. Это классический "refactoring в процессе" — начат, но не завершён.

### 2.2 План решения

**Шаг 1:** Настроить esbuild для сборки `src/` → `recorder.js`

**Шаг 2:** Проверить функциональную эквивалентность

**Шаг 3:** Заменить legacy файл на bundled версию

**Шаг 4:** Удалить legacy файлы

**Целевая структура после рефакторинга:**

```
bookmarklet/
├── src/                 # Исходники (модульные)
│   ├── index.js
│   ├── core/
│   ├── interceptors/
│   ├── ui/
│   └── utils/
├── dist/
│   ├── recorder.js      # Bundled (readable)
│   └── recorder.min.js  # Minified for production
├── build.js             # esbuild script
├── package.json
└── README.md
```

---

## 3. Frontend Analysis

### 3.1 Vue компоненты по размеру

| Component | LOC | Статус | Рекомендация |
|-----------|-----|--------|--------------|
| DashboardView.vue | 687 | ⚠️ | Split: SessionsList, SessionDetail, Stats |
| ResultsView.vue | 521 | ⚠️ | Split: ResultsPanel, ActionsPanel |
| TestCasesView.vue | 500 | ⚠️ | На грани, можно оставить |
| ArticlesView.vue | 495 | ✅ | OK |
| TasksView.vue | 448 | ✅ | OK |
| SettingsView.vue | 447 | ✅ | OK |
| RecorderWidget.vue | 407 | ✅ | OK |
| LoginView.vue | 190 | ✅ | OK |

### 3.2 Stores (Pinia)

| Store | LOC | Статус |
|-------|-----|--------|
| recorder.js | 187 | ✅ OK |
| testcases.js | 99 | ✅ OK |
| articles.js | 97 | ✅ OK |
| sessions.js | 93 | ✅ OK |
| tasks.js | 84 | ✅ OK |
| auth.js | 67 | ✅ OK |

### 3.3 Рекомендуемая структура DashboardView

```
dashboard-vue/src/
├── views/
│   └── DashboardView.vue           # ~100 LOC (container)
└── components/
    └── dashboard/
        ├── SessionsList.vue        # ~200 LOC (table + filters)
        ├── SessionDetailModal.vue  # ~200 LOC (modal content)
        ├── SessionActions.vue      # ~100 LOC (buttons grid)
        └── StatsPanel.vue          # ~80 LOC (statistics)
```

---

## 4. Тестирование

### 4.1 Текущее покрытие

| Файл | LOC | Покрывает |
|------|-----|-----------|
| test_analyzer.py | 314 | analyzer.py |
| test_generators.py | 338 | generators/* |
| test_testit_generator.py | 336 | generators/testit.py |
| test_models.py | 222 | models/* |
| test_providers.py | 189 | providers/* |
| test_api.py | 73 | API endpoints (minimal) |
| **Итого** | **1472** | |

### 4.2 Отсутствующие тесты

| Компонент | Статус | Приоритет |
|-----------|--------|-----------|
| services/session_service.py | ❌ | P1 |
| services/project_service.py | ❌ | P1 |
| repositories/* | ❌ | P2 |
| routers/sessions.py | ❌ | P2 |
| routers/projects.py | ❌ | P2 |
| auth flow (JWT) | ❌ | P1 |

---

## 5. Документация

### 5.1 Статус документов

| Документ | Статус | Действие |
|----------|--------|----------|
| README.md | ✅ | Актуален |
| ROADMAP.md | ⚠️ | Обновить статусы задач |
| CODE_AUDIT_REPORT.md | 🔴 | **Устарел, удалить** |
| PROJECT_SNAPSHOT.md | ⚠️ | Обновить |
| CONTRIBUTING.md | ✅ | OK |
| EXAMPLES.md | ✅ | OK |
| AUDIT_REPORT.md | 🔴 | **Дубликат, удалить** |

### 5.2 Рекомендации

1. Удалить устаревший CODE_AUDIT_REPORT.md
2. Этот документ станет актуальным аудитом
3. Обновить ROADMAP.md после рефакторинга

---

## 6. План рефакторинга WAVE_3.2

### Phase 1: Bookmarklet (4-6 часов)

| # | Задача | Оценка |
|---|--------|--------|
| 1.1 | Настроить esbuild/rollup для src/ | 1h |
| 1.2 | Добавить недостающие функции в src/ (если есть) | 2h |
| 1.3 | Тестирование функциональной эквивалентности | 1h |
| 1.4 | Заменить production recorder.js на bundled | 30m |
| 1.5 | Удалить legacy файлы, обновить CI | 30m |

### Phase 2: Backend Services (6-8 часов)

| # | Задача | Оценка |
|---|--------|--------|
| 2.1 | Создать article_service.py + article_repo.py | 1.5h |
| 2.2 | Создать task_service.py + task_repo.py | 1.5h |
| 2.3 | Создать testcase_service.py (использовать существующий repo) | 1h |
| 2.4 | Создать testrun_service.py + testrun_repo.py | 1h |
| 2.5 | Создать analysis_service.py (вынести из analyzer.py) | 1h |
| 2.6 | Рефакторинг роутеров на использование сервисов | 2h |

### Phase 3: Frontend Split (3-4 часа)

| # | Задача | Оценка |
|---|--------|--------|
| 3.1 | Split DashboardView.vue на компоненты | 2h |
| 3.2 | Split ResultsView.vue | 1.5h |
| 3.3 | Проверка и тестирование | 30m |

### Phase 4: Tests & Docs (2-3 часа)

| # | Задача | Оценка |
|---|--------|--------|
| 4.1 | Тесты для новых сервисов | 1.5h |
| 4.2 | Обновить документацию | 1h |
| 4.3 | Удалить устаревшие документы | 15m |

### Итого

| Phase | Часы | Приоритет |
|-------|------|-----------|
| Phase 1: Bookmarklet | 4-6h | P0 Critical |
| Phase 2: Backend | 6-8h | P1 High |
| Phase 3: Frontend | 3-4h | P2 Medium |
| Phase 4: Tests & Docs | 2-3h | P2 Medium |
| **Всего** | **15-21h** | |

---

## 7. Definition of Done

После рефакторинга WAVE_3.2:

- [ ] Bookmarklet: только один source of truth (src/), legacy удалён
- [ ] Backend: все роутеры используют Service layer
- [ ] Backend: все сервисы используют Repository layer
- [ ] Frontend: нет компонентов >500 LOC
- [ ] Тесты: покрытие сервисов >80%
- [ ] Документация: все документы актуальны, дубликаты удалены
- [ ] CI/CD: сборка и тесты проходят

---

## 8. Файлы для удаления

После завершения рефакторинга удалить:

```
docs/CODE_AUDIT_REPORT.md        # Устарел, заменён этим документом
docs/AUDIT_REPORT.md             # Дубликат
bookmarklet/recorder.js          # Legacy после миграции на src/
bookmarklet/recorder.dev.js      # Legacy
bookmarklet/recorder.js.backup   # Backup не нужен в git
```

---

## Приложение A: Команды для аудита

```bash
# Размеры Python файлов
find backend -name "*.py" | xargs wc -l | sort -rn | head -20

# Размеры JS/Vue файлов
find . -name "*.vue" -o -name "*.js" | grep -v node_modules | grep -v dist | xargs wc -l | sort -rn | head -20

# TODO/FIXME
grep -rn "TODO\|FIXME" --include="*.py" --include="*.js" --include="*.vue"

# Hardcoded localhost
grep -rn "localhost" --include="*.py" --include="*.js" | grep -v node_modules

# Использование Service в роутерах
grep -l "Service" backend/app/routers/*.py
```

---

*Документ создан: 2025-12-05*  
*Следующий аудит: после завершения WAVE_3.2*
