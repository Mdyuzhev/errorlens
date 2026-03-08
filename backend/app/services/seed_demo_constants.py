"""Constants for demo seed data."""

# Demo test cases - разные типы для демонстрации
DEMO_TEST_CASES = [
    {
        "title": "Авторизация: успешный вход с корректными данными",
        "description": "Проверка входа пользователя с валидными учетными данными",
        "preconditions": "Пользователь зарегистрирован в системе",
        "postconditions": "Пользователь авторизован, отображается главная страница",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Авторизация",
        "tags": ["smoke", "auth", "positive"],
        "steps": [
            {"step": 1, "action": "Открыть страницу логина", "expected": "Отображается форма входа"},
            {"step": 2, "action": "Ввести корректный email", "expected": "Email введен"},
            {"step": 3, "action": "Ввести корректный пароль", "expected": "Пароль введен"},
            {"step": 4, "action": "Нажать кнопку 'Войти'", "expected": "Пользователь перенаправлен на главную"},
        ],
    },
    {
        "title": "Авторизация: вход с неверным паролем",
        "description": "Проверка отображения ошибки при неверном пароле",
        "preconditions": "Пользователь зарегистрирован",
        "postconditions": "Отображается сообщение об ошибке",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Авторизация",
        "tags": ["auth", "negative"],
        "steps": [
            {"step": 1, "action": "Открыть страницу логина", "expected": "Форма входа отображается"},
            {"step": 2, "action": "Ввести корректный email", "expected": "Email введен"},
            {"step": 3, "action": "Ввести неверный пароль", "expected": "Пароль введен"},
            {"step": 4, "action": "Нажать 'Войти'", "expected": "Сообщение 'Неверный пароль'"},
        ],
    },
    {
        "title": "Регистрация: создание нового аккаунта",
        "description": "Проверка регистрации нового пользователя",
        "preconditions": "Email не используется в системе",
        "postconditions": "Создан новый аккаунт, отправлено письмо подтверждения",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "Регистрация",
        "tags": ["registration", "smoke", "positive"],
        "steps": [
            {"step": 1, "action": "Открыть страницу регистрации", "expected": "Форма регистрации"},
            {"step": 2, "action": "Заполнить все обязательные поля", "expected": "Поля заполнены"},
            {"step": 3, "action": "Принять пользовательское соглашение", "expected": "Чекбокс отмечен"},
            {"step": 4, "action": "Нажать 'Зарегистрироваться'", "expected": "Аккаунт создан"},
        ],
    },
    {
        "title": "API: GET /sessions возвращает список сессий",
        "description": "Проверка получения списка сессий через API",
        "preconditions": "Авторизованный запрос с JWT токеном",
        "postconditions": "Возвращен JSON со списком сессий",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "API",
        "tags": ["api", "sessions", "positive"],
        "steps": [
            {"step": 1, "action": "Отправить GET /sessions", "expected": "Status 200"},
            {"step": 2, "action": "Проверить структуру ответа", "expected": "Массив объектов"},
            {"step": 3, "action": "Проверить поля сессии", "expected": "id, url, created_at присутствуют"},
        ],
    },
    {
        "title": "API: POST /sessions создает новую сессию",
        "description": "Проверка создания сессии записи ошибок",
        "preconditions": "Валидный JWT токен",
        "postconditions": "Сессия создана в БД",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "API",
        "tags": ["api", "sessions", "positive"],
        "steps": [
            {"step": 1, "action": "POST /sessions с данными", "expected": "Status 201"},
            {"step": 2, "action": "Проверить id в ответе", "expected": "UUID формат"},
            {"step": 3, "action": "GET созданную сессию", "expected": "Данные совпадают"},
        ],
    },
    {
        "title": "UI: Дашборд отображает статистику",
        "description": "Проверка корректного отображения дашборда",
        "preconditions": "Пользователь авторизован",
        "postconditions": "Статистика отображается корректно",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "UI",
        "tags": ["ui", "dashboard", "smoke"],
        "steps": [
            {"step": 1, "action": "Открыть дашборд", "expected": "Страница загружена"},
            {"step": 2, "action": "Проверить счетчик сессий", "expected": "Число >= 0"},
            {"step": 3, "action": "Проверить график", "expected": "График отображается"},
        ],
    },
    {
        "title": "Экспорт: генерация Postman коллекции",
        "description": "Проверка экспорта сессии в Postman формат",
        "preconditions": "Сессия с записанными запросами",
        "postconditions": "Скачан .json файл Postman коллекции",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "Экспорт",
        "tags": ["export", "postman", "integration"],
        "steps": [
            {"step": 1, "action": "Открыть детали сессии", "expected": "Сессия открыта"},
            {"step": 2, "action": "Нажать 'Export Postman'", "expected": "Кнопка активна"},
            {"step": 3, "action": "Проверить скачанный файл", "expected": "Валидный JSON"},
        ],
    },
    {
        "title": "Экспорт: генерация pytest тестов",
        "description": "Проверка генерации Python тестов",
        "preconditions": "Сессия с HTTP запросами",
        "postconditions": "Скачан .py файл с тестами",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Экспорт",
        "tags": ["export", "pytest", "code-gen"],
        "steps": [
            {"step": 1, "action": "Выбрать сессию", "expected": "Сессия выбрана"},
            {"step": 2, "action": "Нажать 'Generate pytest'", "expected": "Генерация запущена"},
            {"step": 3, "action": "Скачать файл", "expected": "test_*.py файл"},
            {"step": 4, "action": "Проверить синтаксис", "expected": "Python валиден"},
        ],
    },
    {
        "title": "AI Анализ: определение severity ошибки",
        "description": "Проверка AI анализа тяжести ошибок",
        "preconditions": "Сессия с JS ошибками",
        "postconditions": "severity определен корректно",
        "priority": "Low",
        "status": "Draft",
        "automation_status": "Manual",
        "folder": "AI",
        "tags": ["ai", "analysis", "severity"],
        "steps": [
            {"step": 1, "action": "Записать сессию с ошибкой", "expected": "Ошибка записана"},
            {"step": 2, "action": "Запустить AI анализ", "expected": "Анализ выполнен"},
            {"step": 3, "action": "Проверить severity", "expected": "low/medium/high/critical"},
        ],
    },
    {
        "title": "Безопасность: XSS в поле поиска",
        "description": "Проверка защиты от XSS атак",
        "preconditions": "Авторизованный пользователь",
        "postconditions": "Скрипт не выполняется",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Security",
        "tags": ["security", "xss", "negative"],
        "steps": [
            {"step": 1, "action": "Ввести <script>alert(1)</script>", "expected": "Текст экранирован"},
            {"step": 2, "action": "Проверить DOM", "expected": "Нет script тега"},
            {"step": 3, "action": "Проверить Network", "expected": "Нет XHR с payload"},
        ],
    },
    # --- P4: дополнительные тест-кейсы ---
    {
        "title": "API: DELETE /sessions удаляет сессию",
        "description": "Проверка удаления сессии через API",
        "preconditions": "Существует сессия, авторизованный запрос",
        "postconditions": "Сессия удалена из БД",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "API",
        "tags": ["api", "sessions", "delete"],
        "steps": [
            {"step": 1, "action": "DELETE /sessions/{id}", "expected": "Status 200"},
            {"step": 2, "action": "GET /sessions/{id}", "expected": "Status 404"},
        ],
    },
    {
        "title": "API: GET /testcases возвращает пагинированный список",
        "description": "Проверка пагинации списка тест-кейсов",
        "preconditions": "Существует >10 тест-кейсов",
        "postconditions": "Возвращен пагинированный список",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "API",
        "tags": ["api", "testcases", "pagination"],
        "steps": [
            {"step": 1, "action": "GET /testcases?limit=5", "expected": "5 элементов в ответе"},
            {"step": 2, "action": "Проверить total count", "expected": "total > 5"},
            {"step": 3, "action": "GET /testcases?offset=5&limit=5", "expected": "Следующая страница"},
        ],
    },
    {
        "title": "UI: Список тест-кейсов сортируется по приоритету",
        "description": "Проверка сортировки тест-кейсов в UI",
        "preconditions": "Есть тест-кейсы разных приоритетов",
        "postconditions": "Тест-кейсы отсортированы",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "UI",
        "tags": ["ui", "testcases", "sorting"],
        "steps": [
            {"step": 1, "action": "Открыть список тест-кейсов", "expected": "Список загружен"},
            {"step": 2, "action": "Нажать сортировку по приоритету", "expected": "Critical первыми"},
            {"step": 3, "action": "Проверить порядок", "expected": "Critical > High > Medium > Low"},
        ],
    },
    {
        "title": "UI: Модальное окно сессии показывает stacktrace",
        "description": "Проверка отображения stacktrace в деталях сессии",
        "preconditions": "Сессия с JS ошибкой и stacktrace",
        "postconditions": "Stacktrace отображается форматированно",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "UI",
        "tags": ["ui", "sessions", "stacktrace"],
        "steps": [
            {"step": 1, "action": "Открыть сессию с ошибкой", "expected": "Детали сессии"},
            {"step": 2, "action": "Найти секцию stacktrace", "expected": "Stacktrace виден"},
            {"step": 3, "action": "Проверить форматирование", "expected": "Моноширинный шрифт, подсветка"},
        ],
    },
    {
        "title": "Security: CSRF токен проверяется на мутирующих запросах",
        "description": "Проверка защиты от CSRF атак",
        "preconditions": "Авторизованный пользователь",
        "postconditions": "Запрос без CSRF токена отклонён",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Security",
        "tags": ["security", "csrf", "negative"],
        "steps": [
            {"step": 1, "action": "POST без CSRF токена", "expected": "Status 403"},
            {"step": 2, "action": "POST с валидным CSRF", "expected": "Status 200"},
        ],
    },
    {
        "title": "Security: SQL injection в параметрах фильтрации",
        "description": "Проверка защиты от SQL injection",
        "preconditions": "Авторизованный пользователь",
        "postconditions": "SQL injection не выполняется",
        "priority": "Critical",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Security",
        "tags": ["security", "sql-injection", "negative"],
        "steps": [
            {"step": 1, "action": "GET /sessions?search=' OR 1=1--", "expected": "Пустой результат или 400"},
            {"step": 2, "action": "Проверить логи БД", "expected": "Параметризованный запрос"},
        ],
    },
    {
        "title": "Авторизация: Refresh token ротация при истечении access token",
        "description": "Проверка автоматического обновления токенов",
        "preconditions": "Access token истёк, refresh token валиден",
        "postconditions": "Выдан новый access token",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Авторизация",
        "tags": ["auth", "jwt", "refresh"],
        "steps": [
            {"step": 1, "action": "Дождаться истечения access token", "expected": "401 на запрос"},
            {"step": 2, "action": "POST /auth/refresh с refresh token", "expected": "Новый access token"},
            {"step": 3, "action": "Повторить запрос с новым token", "expected": "Status 200"},
        ],
    },
    {
        "title": "Авторизация: Logout инвалидирует refresh token",
        "description": "Проверка инвалидации токена при выходе",
        "preconditions": "Пользователь авторизован",
        "postconditions": "Refresh token больше не работает",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Авторизация",
        "tags": ["auth", "logout", "negative"],
        "steps": [
            {"step": 1, "action": "POST /auth/logout", "expected": "Status 200"},
            {"step": 2, "action": "POST /auth/refresh со старым token", "expected": "Status 401"},
        ],
    },
    {
        "title": "Экспорт: REST Assured генерация Java тестов",
        "description": "Проверка генерации Java тестов из сессии",
        "preconditions": "Сессия с HTTP запросами",
        "postconditions": "Скачан .java файл с REST Assured тестами",
        "priority": "Medium",
        "status": "Active",
        "automation_status": "Manual",
        "folder": "Экспорт",
        "tags": ["export", "rest-assured", "java"],
        "steps": [
            {"step": 1, "action": "Выбрать сессию", "expected": "Сессия выбрана"},
            {"step": 2, "action": "Нажать 'Generate REST Assured'", "expected": "Генерация запущена"},
            {"step": 3, "action": "Скачать файл", "expected": ".java файл"},
        ],
    },
    {
        "title": "Регистрация: Регистрация с дублирующимся username",
        "description": "Проверка обработки дубликатов при регистрации",
        "preconditions": "Username уже используется в системе",
        "postconditions": "Отображается ошибка о дубликате",
        "priority": "High",
        "status": "Active",
        "automation_status": "Automated",
        "folder": "Регистрация",
        "tags": ["registration", "negative", "validation"],
        "steps": [
            {"step": 1, "action": "Открыть страницу регистрации", "expected": "Форма регистрации"},
            {"step": 2, "action": "Ввести существующий username", "expected": "Username введён"},
            {"step": 3, "action": "Нажать 'Зарегистрироваться'", "expected": "Ошибка: username занят"},
        ],
    },
]

# Demo tasks for Kanban
DEMO_TASKS = [
    {
        "title": "Добавить OAuth авторизацию через GitHub",
        "description": "Интеграция GitHub OAuth для быстрого входа разработчиков",
        "status": "todo",
        "priority": "high",
        "labels": ["feature", "auth"],
    },
    {
        "title": "Исправить дубликаты в списке сессий",
        "description": "При быстром обновлении страницы сессии дублируются в UI",
        "status": "in_progress",
        "priority": "high",
        "labels": ["bug", "ui"],
    },
    {
        "title": "Добавить фильтрацию по дате",
        "description": "Возможность фильтровать сессии по диапазону дат",
        "status": "todo",
        "priority": "medium",
        "labels": ["feature", "ux"],
    },
    {
        "title": "Оптимизировать запросы к БД",
        "description": "Добавить индексы и пагинацию для больших объемов данных",
        "status": "done",
        "priority": "high",
        "labels": ["performance", "backend"],
    },
    {
        "title": "Написать документацию API",
        "description": "Добавить OpenAPI спецификацию и примеры использования",
        "status": "in_progress",
        "priority": "medium",
        "labels": ["docs", "api"],
    },
    {
        "title": "Добавить темную тему",
        "description": "Переключатель светлая/темная тема в настройках",
        "status": "todo",
        "priority": "low",
        "labels": ["feature", "ui"],
    },
]

# Testcase folder tree structure: {folder_name: [subfolder_names]}
DEMO_TESTCASE_FOLDERS = {
    "Авторизация": ["Позитивные", "Негативные", "JWT"],
    "Регистрация": [],
    "API": ["Sessions", "TestCases", "Auth"],
    "UI": ["Dashboard", "Settings"],
    "Экспорт": ["Postman", "pytest", "Cypress"],
    "AI": ["Анализ ошибок"],
    "Security": ["XSS", "CSRF", "AuthBypass"],
}

# Map: test case folder field → tree folder name
DEMO_TC_FOLDER_MAP = {
    "Авторизация": "Авторизация",
    "Регистрация": "Регистрация",
    "API": "API",
    "UI": "UI",
    "Экспорт": "Экспорт",
    "AI": "AI",
    "Security": "Security",
}

# Welcome article
WELCOME_ARTICLE = {
    "title": "Добро пожаловать в ErrorLens!",
    "slug": "welcome",
    "content": """# Добро пожаловать в ErrorLens!

ErrorLens — инструмент для QA-инженеров, который помогает записывать и анализировать ошибки в браузере.

## Возможности

### Запись сессий
Используйте букмарклет для записи:
- JavaScript ошибок
- Console.log сообщений
- HTTP запросов и ответов
- Скриншотов страницы

### AI Анализ
Встроенный AI анализирует записанные ошибки и выдает:
- Краткое описание проблемы
- Вероятную причину
- Рекомендации по исправлению
- Оценку критичности (severity)

### Экспорт в разные форматы
Генерируйте автотесты из записанных сессий:
- **pytest** — Python тесты
- **REST Assured** — Java тесты
- **Cypress** — E2E тесты
- **Postman** — коллекции для API
- **k6** — нагрузочные тесты

### Интеграции
- **TestIT** — экспорт тест-кейсов
- **YouGile** — создание задач (скоро)

## Быстрый старт

1. Перейдите в **Settings** и установите букмарклет
2. Откройте тестируемый сайт
3. Нажмите букмарклет ErrorLens
4. Выберите режим записи
5. Воспроизведите баг
6. Остановите запись и отправьте на сервер
""",
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

# Demo articles (15+ статей)
DEMO_ARTICLES = [
    {
        "title": "Установка букмарклета в браузер",
        "slug": "install-bookmarklet",
        "content": """# Установка букмарклета в браузер

Букмарклет ErrorLens — это небольшой JavaScript-код, который запускается прямо в браузере и записывает все ошибки и сетевые запросы на тестируемой странице.

## Поддерживаемые браузеры

- Google Chrome (рекомендуется)
- Mozilla Firefox
- Microsoft Edge
- Safari (ограниченная поддержка)

## Инструкция по установке

1. Откройте страницу **Settings** в дашборде ErrorLens
2. Найдите секцию **Bookmarklet**
3. Перетащите кнопку букмарклета на панель закладок браузера
4. Готово! Букмарклет появится в панели закладок

## Проверка установки

После установки откройте любую страницу и нажмите на букмарклет. Должна появиться панель ErrorLens в нижней части экрана с кнопками управления записью.

## Устранение проблем

Если букмарклет не работает, проверьте:
- Не блокируется ли JavaScript на странице
- Разрешены ли cookie для домена ErrorLens
- Не конфликтует ли букмарклет с Content Security Policy сайта
""",
        "excerpt": "Пошаговая инструкция по установке букмарклета ErrorLens в браузер",
        "category": "Начало работы",
        "tags": ["install", "bookmarklet", "setup"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Установка",
    },
    {
        "title": "Быстрый старт за 5 минут",
        "slug": "quick-start",
        "content": """# Быстрый старт за 5 минут

Начните работу с ErrorLens за несколько простых шагов. Это руководство поможет вам записать первую сессию и получить результаты AI-анализа.

## Шаг 1: Регистрация

Перейдите на страницу регистрации и создайте аккаунт. Вам понадобится email и пароль.

## Шаг 2: Установка букмарклета

В разделе Settings найдите кнопку букмарклета и перетащите на панель закладок.

## Шаг 3: Запись сессии

1. Откройте тестируемый сайт
2. Нажмите букмарклет ErrorLens
3. Выберите режим записи (полный или только ошибки)
4. Воспроизведите баг или сценарий
5. Нажмите Stop и отправьте данные

## Шаг 4: Анализ

Откройте записанную сессию в дашборде. Нажмите "Analyze" для запуска AI-анализа. Результат появится через несколько секунд.

## Шаг 5: Экспорт

Выберите формат экспорта (pytest, Postman, Cypress) и скачайте готовые автотесты.
""",
        "excerpt": "Начните работу с ErrorLens за 5 минут — от регистрации до первого анализа",
        "category": "Начало работы",
        "tags": ["quick-start", "tutorial", "beginner"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Начало работы",
    },
    {
        "title": "Первая сессия записи ошибок",
        "slug": "first-session",
        "content": """# Первая сессия записи ошибок

После установки букмарклета вы готовы к записи первой сессии. В этом руководстве разберём весь процесс от начала до конца.

## Подготовка

Убедитесь что:
- Букмарклет установлен в панели закладок
- Вы авторизованы в ErrorLens dashboard
- Тестируемый сайт открыт в браузере

## Запуск записи

1. Перейдите на тестируемую страницу
2. Нажмите букмарклет в панели закладок
3. В появившейся панели выберите режим записи
4. Нажмите кнопку "Start Recording"

## Во время записи

ErrorLens автоматически фиксирует:
- Все JavaScript ошибки и исключения
- Console.log, console.warn, console.error
- HTTP запросы (XHR, Fetch) с заголовками и телом
- Время каждого события

## Завершение записи

Нажмите "Stop" в панели ErrorLens. Данные будут автоматически отправлены на сервер и появятся в дашборде.

## Просмотр результатов

Откройте дашборд ErrorLens. Ваша сессия появится в списке с указанием URL, количества ошибок и времени записи.
""",
        "excerpt": "Подробное руководство по записи первой сессии ошибок с ErrorLens",
        "category": "Начало работы",
        "tags": ["session", "recording", "tutorial"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Начало работы",
    },
    {
        "title": "Режимы записи: полный, только ошибки, только сеть",
        "slug": "recording-modes",
        "content": """# Режимы записи

ErrorLens поддерживает несколько режимов записи, каждый из которых оптимизирован под конкретный сценарий тестирования.

## Полный режим (Full)

Записывает всё: console логи, JS ошибки, HTTP запросы, DOM events. Используйте для комплексного тестирования.

**Когда использовать:** общее исследовательское тестирование, когда не знаете где искать проблему.

## Только ошибки (Errors Only)

Записывает только JavaScript ошибки и console.error. Минимальное влияние на производительность.

**Когда использовать:** мониторинг стабильности, регрессионное тестирование.

## Только сеть (Network Only)

Записывает HTTP запросы и ответы с заголовками и телом. Идеально для API тестирования.

**Когда использовать:** тестирование API, отладка проблем с бэкендом, проверка интеграций.

## Выбор режима

Режим выбирается при запуске записи в панели букмарклета. Его нельзя изменить во время записи — нужно остановить и начать новую сессию.
""",
        "excerpt": "Описание режимов записи ErrorLens и рекомендации по выбору",
        "category": "Руководство пользователя",
        "tags": ["recording", "modes", "configuration"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Запись сессий",
    },
    {
        "title": "Фильтрация HTTP-запросов по домену",
        "slug": "request-filtering",
        "content": """# Фильтрация HTTP-запросов по домену

При записи сессии ErrorLens перехватывает все HTTP запросы страницы. Фильтрация позволяет записывать только нужные запросы и исключать шум от аналитики, CDN и сторонних сервисов.

## Настройка фильтров

В панели букмарклета перед началом записи:

1. Нажмите иконку настроек (шестерёнка)
2. В поле "Include domains" укажите домены для записи
3. В поле "Exclude domains" укажите домены для исключения

## Примеры фильтров

**Записывать только API:** `api.mysite.com`
**Исключить аналитику:** `google-analytics.com, mc.yandex.ru, hotjar.com`
**Несколько доменов:** `api.mysite.com, auth.mysite.com`

## Формат

- Используйте запятую для разделения доменов
- Поддерживаются wildcard: `*.mysite.com`
- Регистр не учитывается

## Поведение по умолчанию

Без фильтров записываются все запросы. Рекомендуется настроить фильтры для чистоты результатов и уменьшения объёма данных.
""",
        "excerpt": "Как настроить фильтрацию HTTP-запросов при записи сессии",
        "category": "Руководство пользователя",
        "tags": ["filtering", "network", "domains"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Запись сессий",
    },
    {
        "title": "Как читать результаты AI-анализа",
        "slug": "ai-analysis-results",
        "content": """# Как читать результаты AI-анализа

AI-анализ ErrorLens обрабатывает записанную сессию и генерирует структурированный отчёт с рекомендациями.

## Структура отчёта

### Summary (Сводка)
Краткое описание найденных проблем в 2-3 предложениях. Содержит общую оценку качества тестируемой страницы.

### Issues (Проблемы)
Список найденных проблем, каждая содержит:
- **Severity** — критичность (critical, high, medium, low, info)
- **Description** — описание проблемы
- **Root Cause** — вероятная причина
- **Recommendation** — рекомендация по исправлению

### Statistics (Статистика)
- Количество JS ошибок
- Количество failed HTTP запросов
- Общее время записи
- Количество console.error

## Интерпретация severity

| Уровень | Значение |
|---------|----------|
| Critical | Блокирует основной функционал |
| High | Серьёзный баг, влияет на UX |
| Medium | Заметная проблема, не критичная |
| Low | Минорный дефект |
| Info | Информация для улучшения |
""",
        "excerpt": "Руководство по интерпретации результатов AI-анализа ErrorLens",
        "category": "Руководство пользователя",
        "tags": ["ai", "analysis", "report"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Анализ результатов",
    },
    {
        "title": "Уровни severity: от info до critical",
        "slug": "severity-levels",
        "content": """# Уровни severity: от info до critical

ErrorLens использует 5-уровневую шкалу критичности для классификации найденных проблем. Понимание каждого уровня помогает приоритизировать исправления.

## Critical

Проблема полностью блокирует основной функционал. Пользователь не может выполнить ключевое действие. Примеры: белый экран, невозможность авторизации, потеря данных.

## High

Серьёзный баг, который заметно влияет на пользовательский опыт. Функционал работает некорректно или с ошибками. Примеры: неправильные расчёты, сломанная навигация.

## Medium

Проблема заметна, но не критична. Есть обходной путь или проблема проявляется редко. Примеры: некорректное отображение на мобильных, медленная загрузка.

## Low

Минорный дефект, не влияющий на функциональность. Примеры: опечатки, незначительные проблемы с вёрсткой, deprecation warnings.

## Info

Информационное замечание для улучшения качества. Не является ошибкой. Примеры: рекомендации по оптимизации, best practices.

## Автоматическая классификация

AI ErrorLens автоматически определяет severity на основе типа ошибки, контекста и потенциального влияния на пользователя.
""",
        "excerpt": "Описание 5 уровней severity в ErrorLens и примеры каждого",
        "category": "Руководство пользователя",
        "tags": ["severity", "classification", "priority"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Анализ результатов",
    },
    {
        "title": "Горячие клавиши и shortcuts",
        "slug": "hotkeys",
        "content": """# Горячие клавиши и shortcuts

ErrorLens поддерживает горячие клавиши для быстрого управления записью и навигацией по дашборду.

## Букмарклет (во время записи)

| Клавиша | Действие |
|---------|----------|
| Ctrl+Shift+E | Запуск/остановка записи |
| Ctrl+Shift+S | Скриншот текущей страницы |
| Ctrl+Shift+X | Закрыть панель ErrorLens |

## Дашборд

| Клавиша | Действие |
|---------|----------|
| / | Фокус на поиск |
| N | Новая сессия / тест-кейс |
| E | Редактировать выбранный элемент |
| Delete | Удалить выбранный элемент |
| Esc | Закрыть модальное окно |
| Ctrl+K | Быстрый поиск (Command Palette) |

## Редактор статей

| Клавиша | Действие |
|---------|----------|
| Ctrl+S | Сохранить статью |
| Ctrl+B | Жирный текст |
| Ctrl+I | Курсив |
| Ctrl+Shift+K | Вставить ссылку |

Горячие клавиши настраиваемы в разделе Settings > Keyboard Shortcuts.
""",
        "excerpt": "Полный список горячих клавиш ErrorLens для букмарклета и дашборда",
        "category": "Руководство пользователя",
        "tags": ["hotkeys", "shortcuts", "productivity"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Руководство пользователя",
    },
    {
        "title": "Настройка интеграции с TestIT",
        "slug": "testit-setup",
        "content": """# Настройка интеграции с TestIT

ErrorLens поддерживает экспорт тест-кейсов в TestIT — популярную систему управления тестированием.

## Получение API ключа

1. Войдите в TestIT
2. Перейдите в Administration > API Keys
3. Создайте новый ключ с правами на создание тест-кейсов
4. Скопируйте ключ

## Настройка в ErrorLens

1. Откройте Settings > Integrations
2. Найдите секцию TestIT
3. Введите:
   - **URL** — адрес вашего TestIT инстанса
   - **API Key** — ключ из предыдущего шага
   - **Project ID** — ID проекта в TestIT
4. Нажмите "Test Connection"
5. Если всё ок — "Save"

## Проверка подключения

После сохранения нажмите "Test Connection". ErrorLens отправит тестовый запрос к TestIT API и покажет результат. При ошибке проверьте URL и права API ключа.

## Маппинг полей

ErrorLens автоматически маппит поля тест-кейсов:

| ErrorLens | TestIT |
|-----------|--------|
| title | Name |
| description | Description |
| steps | Steps |
| priority | Priority |
| tags | Tags |
""",
        "excerpt": "Пошаговая инструкция по подключению ErrorLens к TestIT",
        "category": "Интеграции",
        "tags": ["testit", "integration", "setup"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "TestIT",
    },
    {
        "title": "Экспорт тест-кейсов из сессии",
        "slug": "testit-export",
        "content": """# Экспорт тест-кейсов в TestIT

После настройки интеграции вы можете экспортировать тест-кейсы из ErrorLens напрямую в TestIT.

## Экспорт одного тест-кейса

1. Откройте тест-кейс в ErrorLens
2. Нажмите кнопку "Export" в правом верхнем углу
3. Выберите "TestIT" из списка
4. Выберите раздел (Section) в TestIT для размещения
5. Нажмите "Export"

## Массовый экспорт

1. В списке тест-кейсов отметьте нужные чекбоксами
2. Нажмите "Bulk Export" на панели действий
3. Выберите "TestIT"
4. Настройте маппинг папок ErrorLens → секции TestIT
5. Нажмите "Export All"

## Обработка дубликатов

При экспорте ErrorLens проверяет, нет ли в TestIT тест-кейса с таким же названием. Если дубликат найден, вам предложат обновить существующий или создать новый.

## Статусы экспорта

- **Success** — тест-кейс создан в TestIT
- **Updated** — существующий тест-кейс обновлён
- **Failed** — ошибка, проверьте детали в логе
""",
        "excerpt": "Как экспортировать тест-кейсы из ErrorLens в TestIT",
        "category": "Интеграции",
        "tags": ["testit", "export", "test-cases"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "TestIT",
    },
    {
        "title": "Генерация pytest-тестов из сессии",
        "slug": "export-pytest",
        "content": """# Генерация pytest-тестов из сессии

ErrorLens автоматически генерирует Python тесты на основе записанных HTTP запросов.

## Как это работает

1. ErrorLens анализирует все HTTP запросы из сессии
2. Для каждого запроса генерируется pytest тест-функция
3. Тесты используют библиотеку `requests` для HTTP вызовов
4. Assertions проверяют status code и структуру ответа

## Генерация

1. Откройте записанную сессию
2. Нажмите "Export" > "pytest"
3. Настройте параметры (base_url, auth headers)
4. Нажмите "Generate"
5. Скачайте файл `test_session_<id>.py`

## Пример сгенерированного кода

```python
import requests
import pytest

BASE_URL = "https://api.example.com"

def test_get_users():
    response = requests.get(f"{BASE_URL}/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

## Настройка

Можно указать: base URL, заголовки авторизации, timeout, фильтр по HTTP методам.
""",
        "excerpt": "Генерация pytest тестов из записанной сессии ErrorLens",
        "category": "Интеграции",
        "tags": ["pytest", "export", "code-generation"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Экспорт форматов",
    },
    {
        "title": "Создание Postman-коллекции",
        "slug": "export-postman",
        "content": """# Создание Postman-коллекции

ErrorLens позволяет экспортировать записанные HTTP запросы в формат Postman Collection v2.1.

## Экспорт

1. Откройте сессию с записанными запросами
2. Нажмите "Export" > "Postman"
3. Выберите запросы для включения (по умолчанию все)
4. Нажмите "Download"

## Что включается

- Все HTTP запросы с методом, URL, headers, body
- Группировка по доменам в папки Postman
- Переменные окружения для base URL
- Pre-request скрипты для авторизации

## Импорт в Postman

1. Откройте Postman
2. File > Import
3. Выберите скачанный JSON файл
4. Коллекция появится в sidebar

## Переменные окружения

ErrorLens автоматически выносит повторяющиеся значения в переменные:
- `{{base_url}}` — базовый URL API
- `{{auth_token}}` — токен авторизации

Создайте Environment в Postman и заполните значения переменных.
""",
        "excerpt": "Экспорт HTTP запросов из ErrorLens в Postman коллекцию",
        "category": "Интеграции",
        "tags": ["postman", "export", "api"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Экспорт форматов",
    },
    {
        "title": "Генерация Cypress E2E тестов",
        "slug": "export-cypress",
        "content": """# Генерация Cypress E2E тестов

ErrorLens генерирует E2E тесты для Cypress на основе записанных сессий.

## Как это работает

ErrorLens анализирует записанную сессию и создаёт Cypress спецификацию, которая воспроизводит HTTP-взаимодействия с API через `cy.request()`.

## Генерация

1. Откройте сессию
2. Export > Cypress
3. Настройте base URL
4. Download файл `.cy.js`

## Пример

```javascript
describe('Session: Login Flow', () => {
  it('should login successfully', () => {
    cy.request({
      method: 'POST',
      url: '/api/auth/login',
      body: { email: 'user@test.com', password: '***' }
    }).then((response) => {
      expect(response.status).to.eq(200)
      expect(response.body).to.have.property('token')
    })
  })
})
```

## Интеграция в проект

1. Скопируйте файл в `cypress/e2e/`
2. Обновите `cypress.config.js` с нужным `baseUrl`
3. Запустите: `npx cypress run`

## Ограничения

Cypress тесты генерируются только для API запросов (cy.request). UI-взаимодействия (клики, ввод) не записываются — для этого используйте Cypress Studio.
""",
        "excerpt": "Автоматическая генерация Cypress E2E тестов из записанных сессий",
        "category": "Интеграции",
        "tags": ["cypress", "e2e", "export"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "Экспорт форматов",
    },
    {
        "title": "Аутентификация: JWT токены",
        "slug": "api-auth",
        "content": """# Аутентификация: JWT токены

ErrorLens API использует JWT (JSON Web Tokens) для аутентификации. Все защищённые эндпоинты требуют валидный access token в заголовке Authorization.

## Получение токенов

```
POST /auth/login
Content-Type: application/json

{"username": "user@example.com", "password": "secret"}
```

Ответ:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

## Использование

Добавьте токен в заголовок:
```
Authorization: Bearer eyJ...
```

## Время жизни

| Токен | TTL |
|-------|-----|
| Access token | 30 минут |
| Refresh token | 7 дней |

## Обновление access token

```
POST /auth/refresh
Content-Type: application/json

{"refresh_token": "eyJ..."}
```

## Ошибки

| Status | Причина |
|--------|---------|
| 401 | Токен отсутствует, истёк или невалиден |
| 403 | Недостаточно прав (не admin) |
""",
        "excerpt": "Документация по JWT аутентификации в ErrorLens API",
        "category": "API Reference",
        "tags": ["api", "auth", "jwt"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "API Reference",
    },
    {
        "title": "Справочник: Sessions API",
        "slug": "api-sessions",
        "content": """# Справочник: Sessions API

API для управления записанными сессиями. Все эндпоинты требуют авторизации.

## Список сессий

```
GET /sessions?limit=20&offset=0&search=example
```

Параметры:
- `limit` — количество (default: 20, max: 100)
- `offset` — смещение для пагинации
- `search` — поиск по URL
- `project_id` — фильтр по проекту

Ответ:
```json
{
  "items": [
    {
      "id": "uuid",
      "url": "https://example.com",
      "error_count": 5,
      "request_count": 42,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 150
}
```

## Получение сессии

```
GET /sessions/{id}
```

## Создание сессии

```
POST /sessions
Content-Type: application/json

{
  "url": "https://example.com",
  "user_agent": "Mozilla/5.0...",
  "console_logs": [...],
  "network_errors": [...],
  "js_exceptions": [...]
}
```

## Удаление сессии

```
DELETE /sessions/{id}
```

Возвращает 200 при успехе, 404 если сессия не найдена.
""",
        "excerpt": "Полный справочник Sessions API в ErrorLens",
        "category": "API Reference",
        "tags": ["api", "sessions", "reference"],
        "status": "published",
        "author": "ErrorLens Team",
        "folder_key": "API Reference",
    },
]
