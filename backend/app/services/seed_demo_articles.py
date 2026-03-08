"""Constants for demo seed data — articles and article folders."""

# Welcome article
WELCOME_ARTICLE = {
    "title": "Добро пожаловать в ErrorLens!",
    "slug": "welcome",
    "content": (
        "# Добро пожаловать в ErrorLens!\n\n"
        "ErrorLens — инструмент для QA-инженеров, который помогает записывать "
        "и анализировать ошибки в браузере.\n\n"
        "## Возможности\n\n"
        "- Запись сессий (JS ошибки, console, HTTP запросы, скриншоты)\n"
        "- AI Анализ (описание, причина, рекомендации, severity)\n"
        "- Экспорт (pytest, REST Assured, Cypress, Postman, k6)\n"
        "- Интеграции (TestIT, YouGile)\n\n"
        "## Быстрый старт\n\n"
        "1. Перейдите в **Settings** и установите букмарклет\n"
        "2. Откройте тестируемый сайт\n"
        "3. Нажмите букмарклет ErrorLens\n"
        "4. Выберите режим записи\n"
        "5. Воспроизведите баг\n"
        "6. Остановите запись и отправьте на сервер\n"
    ),
    "excerpt": "Краткое руководство по началу работы с ErrorLens",
    "category": "Getting Started",
    "tags": ["guide", "quick-start", "tutorial"],
    "status": "published",
    "author": "ErrorLens Team",
}

# Article folder tree structure
DEMO_ARTICLE_FOLDERS = {
    "Начало работы": ["Установка"],
    "Руководство пользователя": ["Запись сессий", "Анализ результатов"],
    "Интеграции": ["TestIT", "Экспорт форматов"],
    "API Reference": [],
}

# Map: article folder_key → folder name for lookup
DEMO_ARTICLE_FOLDER_MAP = {
    "Установка": "Установка",
    "Начало работы": "Начало работы",
    "Запись сессий": "Запись сессий",
    "Анализ результатов": "Анализ результатов",
    "Руководство пользователя": "Руководство пользователя",
    "TestIT": "TestIT",
    "Экспорт форматов": "Экспорт форматов",
    "API Reference": "API Reference",
}


def _art(title: str, slug: str, content: str, excerpt: str,
         category: str, tags: list[str], folder_key: str) -> dict:
    """Helper to create article dict with common defaults."""
    return {
        "title": title, "slug": slug, "content": content,
        "excerpt": excerpt, "category": category, "tags": tags,
        "status": "published", "author": "ErrorLens Team",
        "folder_key": folder_key,
    }


# Demo articles (15 статей)
DEMO_ARTICLES = [
    _art(
        "Установка букмарклета в браузер", "install-bookmarklet",
        "# Установка букмарклета\n\nБукмарклет ErrorLens — JavaScript-код, "
        "записывающий ошибки и сетевые запросы на странице.\n\n"
        "## Поддерживаемые браузеры\n\nChrome, Firefox, Edge, Safari.\n\n"
        "## Инструкция\n\n1. Откройте Settings > Bookmarklet\n"
        "2. Перетащите кнопку на панель закладок\n"
        "3. Откройте тестируемую страницу и нажмите букмарклет\n\n"
        "## Устранение проблем\n\nПроверьте: JavaScript не заблокирован, "
        "cookie разрешены, нет конфликта с CSP сайта.",
        "Пошаговая инструкция по установке букмарклета ErrorLens",
        "Начало работы", ["install", "bookmarklet", "setup"], "Установка",
    ),
    _art(
        "Быстрый старт за 5 минут", "quick-start",
        "# Быстрый старт за 5 минут\n\n"
        "## Шаг 1: Регистрация\nСоздайте аккаунт на странице регистрации.\n\n"
        "## Шаг 2: Букмарклет\nВ Settings перетащите кнопку на панель закладок.\n\n"
        "## Шаг 3: Запись\nОткройте сайт, нажмите букмарклет, воспроизведите баг, Stop.\n\n"
        "## Шаг 4: Анализ\nОткройте сессию, нажмите Analyze.\n\n"
        "## Шаг 5: Экспорт\nВыберите формат (pytest, Postman, Cypress) и скачайте.",
        "Начните работу с ErrorLens за 5 минут",
        "Начало работы", ["quick-start", "tutorial", "beginner"], "Начало работы",
    ),
    _art(
        "Первая сессия записи ошибок", "first-session",
        "# Первая сессия записи ошибок\n\n"
        "## Подготовка\nБукмарклет установлен, вы авторизованы, тестируемый сайт открыт.\n\n"
        "## Запуск записи\n1. Перейдите на тестируемую страницу\n"
        "2. Нажмите букмарклет\n3. Выберите режим записи\n4. Start Recording\n\n"
        "## Во время записи\nErrorLens фиксирует: JS ошибки, console.log/warn/error, "
        "HTTP запросы (XHR, Fetch), время каждого события.\n\n"
        "## Завершение\nНажмите Stop — данные отправляются на сервер автоматически.",
        "Подробное руководство по записи первой сессии ошибок",
        "Начало работы", ["session", "recording", "tutorial"], "Начало работы",
    ),
    _art(
        "Режимы записи: полный, только ошибки, только сеть", "recording-modes",
        "# Режимы записи\n\n"
        "## Полный режим (Full)\nВсё: console, JS ошибки, HTTP, DOM events. "
        "Для исследовательского тестирования.\n\n"
        "## Только ошибки (Errors Only)\nТолько JS ошибки и console.error. "
        "Минимальное влияние на производительность.\n\n"
        "## Только сеть (Network Only)\nHTTP запросы и ответы. Для API тестирования.\n\n"
        "## Выбор режима\nРежим выбирается при запуске. Изменить во время записи нельзя.",
        "Описание режимов записи ErrorLens и рекомендации по выбору",
        "Руководство пользователя", ["recording", "modes", "configuration"], "Запись сессий",
    ),
    _art(
        "Фильтрация HTTP-запросов по домену", "request-filtering",
        "# Фильтрация HTTP-запросов по домену\n\n"
        "## Настройка\nВ панели букмарклета перед записью: Include domains / Exclude domains.\n\n"
        "## Примеры\n- Только API: `api.mysite.com`\n"
        "- Исключить аналитику: `google-analytics.com, mc.yandex.ru`\n"
        "- Wildcard: `*.mysite.com`\n\n"
        "## По умолчанию\nБез фильтров записываются все запросы.",
        "Как настроить фильтрацию HTTP-запросов при записи сессии",
        "Руководство пользователя", ["filtering", "network", "domains"], "Запись сессий",
    ),
    _art(
        "Как читать результаты AI-анализа", "ai-analysis-results",
        "# Как читать результаты AI-анализа\n\n"
        "## Структура отчёта\n"
        "- **Summary** — сводка в 2-3 предложениях\n"
        "- **Issues** — список проблем (severity, description, root cause, recommendation)\n"
        "- **Statistics** — JS ошибки, failed HTTP, время записи, console.error\n\n"
        "## Severity\n"
        "| Уровень | Значение |\n|---------|----------|\n"
        "| Critical | Блокирует основной функционал |\n"
        "| High | Серьёзный баг, влияет на UX |\n"
        "| Medium | Заметная проблема, не критичная |\n"
        "| Low | Минорный дефект |\n| Info | Информация для улучшения |",
        "Руководство по интерпретации результатов AI-анализа ErrorLens",
        "Руководство пользователя", ["ai", "analysis", "report"], "Анализ результатов",
    ),
    _art(
        "Уровни severity: от info до critical", "severity-levels",
        "# Уровни severity\n\n"
        "ErrorLens использует 5-уровневую шкалу критичности.\n\n"
        "## Critical\nПолная блокировка функционала. Белый экран, невозможность авторизации.\n\n"
        "## High\nСерьёзный баг, некорректные расчёты, сломанная навигация.\n\n"
        "## Medium\nЗаметная проблема, есть обходной путь. Плохое отображение на мобильных.\n\n"
        "## Low\nМинорный дефект: опечатки, мелкие проблемы с вёрсткой.\n\n"
        "## Info\nИнформационное замечание, не ошибка. Рекомендации по оптимизации.\n\n"
        "AI автоматически определяет severity на основе типа ошибки и контекста.",
        "Описание 5 уровней severity в ErrorLens",
        "Руководство пользователя", ["severity", "classification", "priority"],
        "Анализ результатов",
    ),
    _art(
        "Горячие клавиши и shortcuts", "hotkeys",
        "# Горячие клавиши\n\n"
        "## Букмарклет\n"
        "| Клавиша | Действие |\n|---------|----------|\n"
        "| Ctrl+Shift+E | Запуск/остановка записи |\n"
        "| Ctrl+Shift+S | Скриншот страницы |\n"
        "| Ctrl+Shift+X | Закрыть панель |\n\n"
        "## Дашборд\n"
        "| Клавиша | Действие |\n|---------|----------|\n"
        "| / | Фокус на поиск |\n| N | Новый элемент |\n"
        "| E | Редактировать |\n| Delete | Удалить |\n"
        "| Esc | Закрыть модалку |\n| Ctrl+K | Command Palette |",
        "Полный список горячих клавиш ErrorLens",
        "Руководство пользователя", ["hotkeys", "shortcuts", "productivity"],
        "Руководство пользователя",
    ),
    _art(
        "Настройка интеграции с TestIT", "testit-setup",
        "# Настройка интеграции с TestIT\n\n"
        "## Получение API ключа\n"
        "1. Войдите в TestIT\n2. Administration > API Keys\n"
        "3. Создайте ключ с правами на создание тест-кейсов\n\n"
        "## Настройка в ErrorLens\n"
        "1. Settings > Integrations > TestIT\n"
        "2. Введите URL, API Key, Project ID\n"
        "3. Test Connection > Save\n\n"
        "## Маппинг полей\n"
        "| ErrorLens | TestIT |\n|-----------|--------|\n"
        "| title | Name |\n| description | Description |\n"
        "| steps | Steps |\n| priority | Priority |",
        "Пошаговая инструкция по подключению ErrorLens к TestIT",
        "Интеграции", ["testit", "integration", "setup"], "TestIT",
    ),
    _art(
        "Экспорт тест-кейсов в TestIT", "testit-export",
        "# Экспорт тест-кейсов в TestIT\n\n"
        "## Экспорт одного тест-кейса\n"
        "Откройте тест-кейс > Export > TestIT > выберите раздел > Export.\n\n"
        "## Массовый экспорт\n"
        "Отметьте тест-кейсы > Bulk Export > TestIT > настройте маппинг > Export All.\n\n"
        "## Обработка дубликатов\n"
        "При экспорте проверяется наличие тест-кейса с таким же названием. "
        "Предлагается обновить существующий или создать новый.\n\n"
        "## Статусы: Success, Updated, Failed.",
        "Как экспортировать тест-кейсы из ErrorLens в TestIT",
        "Интеграции", ["testit", "export", "test-cases"], "TestIT",
    ),
    _art(
        "Генерация pytest-тестов из сессии", "export-pytest",
        "# Генерация pytest-тестов\n\n"
        "ErrorLens генерирует Python тесты из записанных HTTP запросов.\n\n"
        "## Процесс\n1. Откройте сессию\n2. Export > pytest\n"
        "3. Настройте base_url, auth headers\n4. Generate > Download\n\n"
        "## Пример\n```python\nimport requests\n\n"
        "def test_get_users():\n"
        "    response = requests.get(f'{BASE_URL}/users')\n"
        "    assert response.status_code == 200\n```\n\n"
        "Можно указать: base URL, заголовки, timeout, фильтр по HTTP методам.",
        "Генерация pytest тестов из записанной сессии ErrorLens",
        "Интеграции", ["pytest", "export", "code-generation"], "Экспорт форматов",
    ),
    _art(
        "Создание Postman-коллекции", "export-postman",
        "# Создание Postman-коллекции\n\n"
        "Экспорт HTTP запросов в Postman Collection v2.1.\n\n"
        "## Экспорт\nОткройте сессию > Export > Postman > Download.\n\n"
        "## Что включается\n- HTTP запросы с method, URL, headers, body\n"
        "- Группировка по доменам\n- Переменные {{base_url}}, {{auth_token}}\n\n"
        "## Импорт в Postman\nFile > Import > выберите JSON файл.",
        "Экспорт HTTP запросов из ErrorLens в Postman коллекцию",
        "Интеграции", ["postman", "export", "api"], "Экспорт форматов",
    ),
    _art(
        "Генерация Cypress E2E тестов", "export-cypress",
        "# Генерация Cypress E2E тестов\n\n"
        "ErrorLens создаёт Cypress спецификацию из записанных сессий.\n\n"
        "## Генерация\nОткройте сессию > Export > Cypress > Download `.cy.js`\n\n"
        "## Пример\n```javascript\ndescribe('Login Flow', () => {\n"
        "  it('should login', () => {\n"
        "    cy.request('POST', '/api/auth/login', {email: 'user@test.com'})\n"
        "      .then(r => expect(r.status).to.eq(200))\n  })\n})\n```\n\n"
        "## Ограничения\nТолько API запросы (cy.request). UI-взаимодействия не записываются.",
        "Автоматическая генерация Cypress E2E тестов из записанных сессий",
        "Интеграции", ["cypress", "e2e", "export"], "Экспорт форматов",
    ),
    _art(
        "Аутентификация: JWT токены", "api-auth",
        "# Аутентификация: JWT токены\n\n"
        "## Получение токенов\n`POST /auth/login` с {username, password}. "
        "Ответ: {access_token, refresh_token, token_type}.\n\n"
        "## Использование\n`Authorization: Bearer eyJ...`\n\n"
        "## TTL\n- Access token: 30 минут\n- Refresh token: 7 дней\n\n"
        "## Обновление\n`POST /auth/refresh` с {refresh_token}.\n\n"
        "## Ошибки\n- 401: токен отсутствует/истёк/невалиден\n"
        "- 403: недостаточно прав (не admin)",
        "Документация по JWT аутентификации в ErrorLens API",
        "API Reference", ["api", "auth", "jwt"], "API Reference",
    ),
    _art(
        "Справочник: Sessions API", "api-sessions",
        "# Справочник: Sessions API\n\n"
        "Все эндпоинты требуют авторизации.\n\n"
        "## GET /sessions\nПараметры: limit (20), offset, search, project_id. "
        "Ответ: {items: [...], total: N}.\n\n"
        "## GET /sessions/{id}\nДетали сессии.\n\n"
        "## POST /sessions\nТело: {url, user_agent, console_logs, network_errors, js_exceptions}.\n\n"
        "## DELETE /sessions/{id}\n200 при успехе, 404 если не найдена.",
        "Полный справочник Sessions API в ErrorLens",
        "API Reference", ["api", "sessions", "reference"], "API Reference",
    ),
]
