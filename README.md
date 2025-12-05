# ErrorLens

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/Mdyuzhev/errorlens/actions/workflows/ci.yml/badge.svg)](https://github.com/Mdyuzhev/errorlens/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Легковесный инструмент записи ошибок для QA-инженеров. Захватывает ошибки браузера и получает AI-анализ — без расширений, без регистрации, работает везде.

## Что это?

ErrorLens — это букмарклет, который записывает ошибки браузера в реальном времени. Когда вы тестируете веб-приложение и сталкиваетесь с багом, просто кликните на букмарклет, воспроизведите ошибку, кликните снова — и получите мгновенный AI-анализ того, что пошло не так.

Идеально для QA-инженеров, которым надоело вручную копировать логи консоли и сетевые ошибки.

## Возможности

- **Запись в один клик** — Без установки, без настройки, просто перетащите закладку
- **Захватывает всё** — Логи консоли, сетевые ошибки, JS-исключения
- **AI-анализ** — Мгновенные инсайты о проблеме и способах её решения
- **Dashboard** — Просмотр истории всех записанных сессий
- **Генератор тикетов** — Создание Jira/GitHub issues из анализа
- **Экспорт тестов** — Генерация pytest или Postman коллекций
- **Запуск тестов** — Выполнение тестов прямо из dashboard
- **Экспорт** — Копирование в буфер или скачивание в Markdown
- **Rate Limiting** — Защита от abuse (10 запросов/день для анонимов)

## Быстрый старт

### Использование

1. Перейдите на [errorlens.github.io](https://mdyuzhev.github.io/errorlens)
2. Перетащите кнопку "ErrorLens" в панель закладок браузера
3. Откройте страницу, которую хотите протестировать
4. Кликните на закладку — появится виджет записи
5. Воспроизведите баг
6. Нажмите "Остановить и отправить" для анализа
7. Скопируйте результат или экспортируйте в Markdown

### Локальная разработка

```bash
# Клонируйте репозиторий
git clone https://github.com/Mdyuzhev/errorlens.git
cd errorlens

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # или `venv\Scripts\activate` на Windows
pip install -r requirements.txt

# Создайте .env файл с API ключом
cp .env.example .env
# Отредактируйте .env и добавьте GROQ_API_KEY или GEMINI_API_KEY

# Запустите сервер
uvicorn app.main:app --reload

# Букмарклет — просто JS файл, сборка не нужна
```

### Docker (рекомендуемый способ)

Полный стек с landing page и API через nginx:

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/Mdyuzhev/errorlens.git
cd errorlens

# 2. Создайте .env файл (или экспортируйте переменные)
export GROQ_API_KEY=your_groq_key
# или
export GEMINI_API_KEY=your_gemini_key

# 3. Запустите
docker-compose up --build

# 4. Готово!
# - Landing page: http://localhost:3000
# - API напрямую: http://localhost:8000
# - API через nginx: http://localhost:3000/api/
# - Swagger docs: http://localhost:8000/docs
```

Только backend:

```bash
cd backend
docker build -t errorlens-backend .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key errorlens-backend
```

## Конфигурация

Создайте файл `.env` в директории `backend/`:

```env
# LLM провайдер (groq или gemini)
LLM_PROVIDER=groq

# API ключи (нужен хотя бы один)
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Получение API ключей

- **Groq** (рекомендуется): [console.groq.com](https://console.groq.com) — бесплатно, быстро
- **Gemini**: [aistudio.google.com](https://aistudio.google.com) — щедрый бесплатный tier

## API документация

После запуска backend автоматическая документация доступна по адресам:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Проверка работоспособности |
| POST | `/analyze` | AI-анализ ошибок |
| POST | `/sessions` | Создание сессии |
| GET | `/sessions` | Список сессий |
| GET | `/sessions/{id}` | Детали сессии |
| POST | `/export/postman` | Экспорт в Postman |
| POST | `/export/pytest` | Экспорт в pytest |
| POST | `/tickets/generate` | Генерация тикета |
| POST | `/tests/run` | Запуск тестов |

## Технологии

- **Frontend:** Vue 3 (Composition API) + Vanilla JS (bookmarklet)
- **Backend:** Python 3.11+ / FastAPI / Pydantic
- **Database:** SQLite + SQLAlchemy (async)
- **AI:** Groq Llama 3.3 70B / Google Gemini
- **Container:** Docker + nginx
- **CI/CD:** GitHub Actions
- **Build:** esbuild (bookmarklet bundling)

## Архитектура

```
errorlens/
├── backend/                    # FastAPI сервер
│   ├── app/
│   │   ├── models/            # SQLAlchemy модели (Session, User, Task, etc.)
│   │   ├── repositories/      # Data Access Layer (article_repo, task_repo, etc.)
│   │   ├── services/          # Business Logic Layer
│   │   │   ├── article_service.py
│   │   │   ├── task_service.py
│   │   │   ├── testcase_service.py
│   │   │   ├── testrun_service.py
│   │   │   └── analysis_service.py
│   │   ├── routers/           # API endpoints
│   │   └── middleware/        # Auth, rate limiting
│   └── tests/                 # pytest тесты
│
├── bookmarklet/               # Клиентский recorder
│   ├── src/                   # ES модули
│   │   ├── recorder.js        # Основная логика записи
│   │   ├── network.js         # Перехват fetch/XHR
│   │   ├── ui.js              # Widget UI
│   │   └── index.js           # Entry point
│   ├── dist/                  # Собранные бандлы (esbuild)
│   │   ├── recorder.js        # Development build
│   │   └── recorder.min.js    # Production build (minified)
│   └── esbuild.config.js      # Build configuration
│
├── dashboard-vue/             # Vue 3 dashboard
│   └── src/
│       ├── views/             # Page components
│       │   ├── DashboardView.vue
│       │   └── ResultsView.vue
│       ├── components/        # Reusable components
│       │   ├── dashboard/     # Session-related components
│       │   │   ├── SessionFilters.vue
│       │   │   ├── SessionCard.vue
│       │   │   └── SessionDetailModal.vue
│       │   └── results/       # Test results components
│       │       ├── StatsSummary.vue
│       │       ├── DonutChart.vue
│       │       └── TestRunCard.vue
│       └── services/          # API client
│
└── landing/                   # GitHub Pages landing
```

### Backend Architecture

Трёхслойная архитектура:

```
Router (HTTP) → Service (Business Logic) → Repository (Data Access) → Model (DB)
```

**Routers** — Тонкий слой HTTP, валидация запросов, вызов сервисов
**Services** — Бизнес-логика, трансформация данных, orchestration
**Repositories** — CRUD операции, SQL queries, изоляция БД

## Статус проекта

См. [ROADMAP.md](ROADMAP.md) для подробного статуса задач.

## Примеры использования

См. [docs/EXAMPLES.md](docs/EXAMPLES.md) для примеров реальных сценариев.

## Участие в разработке

Контрибьюции приветствуются! Пожалуйста, прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) перед отправкой PR.

## Лицензия

MIT — см. [LICENSE](LICENSE) для деталей.
