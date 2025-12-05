# 🤖 AGENT TASK: EL_Bot v5 - Full Upgrade

## Контекст
Ты работаешь над Telegram ботом EL_Bot для проекта ErrorLens.
Текущая версия: `bot.py` (v2.1) + `bot_v4.py` (с мониторингом)
Нужно создать `bot_v5.py` - объединить лучшее и добавить новый функционал.

## Файлы для изучения
```
/home/ubuntu/workspace/errorlens/el-bot-files/bot.py      # v2.1 - GitHub интеграция
/home/ubuntu/workspace/errorlens/el-bot-files/bot_v4.py   # v4 - мониторинг агента
```

## Задача 1: InlineKeyboard кнопки с эмодзи

При `/start` показывать красивое меню с кнопками:

```
🤖 EL_Bot v5

Добро пожаловать! Выберите действие:

[🚀 Exec]  [📋 Tasks]  [📊 Status]
[🔬 Lab]   [📝 Todo]   [📚 Help]
```

Кнопки должны вызывать соответствующие команды через CallbackQuery.

## Задача 2: Подробная справка /help

```
📚 EL_Bot v5 - Справка

━━━ 🚀 Выполнение задач ━━━
/exec - Запустить задачу агента
  • Показывает список из 10 последних задач
  • Выбираете номер кнопкой
  • Агент выполняет задачу в контейнере
  • Получаете уведомление по завершению

━━━ 📋 Управление задачами ━━━
/tasks - Список задач в очереди
/clear - Очистить очередь задач
📎 Отправьте .md файл - добавить задачу

━━━ 📝 GitHub Issues ━━━
/todo <текст> - Создать Issue
/todo Заголовок | Описание
/list - Последние 5 Issues
💬 Просто текст → создаёт Issue

━━━ 🔬 Мониторинг ━━━
/lab - Статус домашнего сервера
/status - Статус текущей задачи

━━━ ℹ️ Прочее ━━━
/start - Главное меню
/help - Эта справка
```

## Задача 3: Workflow для /exec с кнопками

**Шаг 1:** Пользователь нажимает 🚀 Exec или /exec
**Шаг 2:** Бот показывает список задач с кнопками:

```
📋 Выберите задачу:

[1️⃣ Fix auth bug]
[2️⃣ Add dark mode]
[3️⃣ Refactor API]
...до 10 задач...

[❌ Отмена]
```

**Шаг 3:** Пользователь нажимает кнопку с номером
**Шаг 4:** Бот запускает задачу и показывает прогресс
**Шаг 5:** По завершению - уведомление с результатом

Используй `InlineKeyboardButton` с `callback_data` типа `exec_1`, `exec_2`, etc.

## Задача 4: Команда /lab - мониторинг сервера

Проверять статус сервисов на 192.168.1.74 через SSH:

```python
SERVICES_TO_CHECK = [
    {"name": "Docker", "cmd": "systemctl is-active docker"},
    {"name": "Claude Agent", "cmd": "docker ps | grep claude-agent"},
    {"name": "PostgreSQL", "cmd": "docker ps | grep postgres"},
    {"name": "Nginx", "cmd": "systemctl is-active nginx"},
    {"name": "SSH", "cmd": "echo ok"},  # если дошли сюда - SSH работает
]
```

**Формат ответа - всё ОК:**
```
🔬 LAB Status

✅ ВСЁ РАБОТАЕТ ШТАТНО

━━━ Сервисы ━━━
✅ Docker: active
✅ Claude Agent: running
✅ PostgreSQL: running
✅ Nginx: active
✅ SSH: connected

🕐 Проверено: 15:42:30
```

**Формат ответа - есть проблемы:**
```
🔬 LAB Status

⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ

━━━ Сервисы ━━━
✅ Docker: active
❌ Claude Agent: not running
✅ PostgreSQL: running
❌ Nginx: inactive
✅ SSH: connected

━━━ Рекомендации ━━━
🔧 Claude Agent: cd ~/projects/claude-agent && docker-compose up -d
🔧 Nginx: sudo systemctl start nginx

🕐 Проверено: 15:42:30
```

## Задача 5: Рефакторинг кода

1. Чистый, читаемый код с комментариями на английском
2. Все строки интерфейса на русском
3. Использовать `InlineKeyboardMarkup` и `CallbackQueryHandler`
4. Сохранить всю логику из v2.1 (GitHub issues, project integration)
5. Добавить мониторинг из v4 (agent_state, monitor task)
6. Структура:
   - Constants
   - Helper functions
   - Command handlers
   - Callback handlers
   - Main

## Технические требования

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
```

SSH команды выполнять через:
```python
ssh_base = [
    "ssh", "-i", "/ssh/id_ed25519",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "flomaster@192.168.1.74"
]
```

## Результат

Создай файл `/home/ubuntu/workspace/errorlens/el-bot-files/bot_v5.py`

## После завершения

**ВАЖНО:** После того как закончишь работу, отправь статус в Telegram используя curl:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "'"${TELEGRAM_ADMIN_ID}"'",
    "text": "✅ AGENT TASK COMPLETED\n\n📦 Task: EL_Bot v5 Upgrade\n📁 File: bot_v5.py\n\n🎯 Что сделано:\n• InlineKeyboard меню\n• /help справка\n• /exec с кнопками выбора\n• /lab мониторинг сервера\n• Рефакторинг кода\n\n🚀 Готово к деплою!",
    "parse_mode": "HTML"
  }'
```

Переменные окружения TELEGRAM_BOT_TOKEN и TELEGRAM_ADMIN_ID уже установлены в контейнере.
