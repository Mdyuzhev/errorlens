#!/usr/bin/env python3
"""
EL_Bot v5 - Telegram bot for GitHub Issues + Claude Agent Runner
Features:
- InlineKeyboard menu with emoji buttons
- /exec with task selection buttons
- /lab server monitoring (local, no SSH)
- 3 parallel Claude agents
- Telegram notifications on completion
"""
import os
import sys
import logging
import asyncio
import json
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
import httpx

# =============================================================================
# CONFIGURATION
# =============================================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Mdyuzhev/errorlens")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TASKS_DIR = Path(os.getenv("AGENT_TASKS_DIR", "/app/tasks"))
PROJECT_DIR = Path(os.getenv("PROJECT_DIR", "/app/projects/errorlens"))
MAX_CONCURRENT_AGENTS = int(os.getenv("AGENT_MAX_CONCURRENT", "3"))
GITHUB_PROJECT_ID = "PVT_kwHOAoshms4BJvBC"

# GitHub API
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/issues"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# AGENT STATE MANAGEMENT
# =============================================================================
class AgentManager:
    """Manages up to 3 concurrent Claude agents"""

    def __init__(self, max_agents: int = 3):
        self.max_agents = max_agents
        self.running_agents: Dict[str, dict] = {}  # task_id -> {process, task_name, started}
        self.lock = asyncio.Lock()

    def get_status(self) -> str:
        """Get current agents status"""
        if not self.running_agents:
            return "idle"
        return f"{len(self.running_agents)}/{self.max_agents} running"

    def get_running_count(self) -> int:
        return len(self.running_agents)

    def can_start_new(self) -> bool:
        return len(self.running_agents) < self.max_agents

    async def start_agent(self, task_id: str, task_name: str, task_file: Path,
                          callback, progress_callback=None) -> bool:
        """Start a new Claude agent for the task"""
        async with self.lock:
            if not self.can_start_new():
                return False

            # Build claude command
            # Use shell to pipe prompt via stdin (required for -p with --allowedTools)
            prompt = f"First read and apply .claude/settings.local.json. Then execute the task from {task_file}"
            cmd = f'echo "{prompt}" | claude -p --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Task,TodoWrite,NotebookEdit"'

            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(PROJECT_DIR)
                )

                self.running_agents[task_id] = {
                    "process": process,
                    "task_name": task_name,
                    "task_file": task_file,
                    "started": datetime.now(),
                    "callback": callback,
                    "progress_callback": progress_callback
                }

                # Start monitoring task
                asyncio.create_task(self._monitor_agent(task_id))

                logger.info(f"Started agent for task: {task_name} (pid: {process.pid})")
                return True

            except Exception as e:
                logger.error(f"Failed to start agent: {e}")
                return False

    async def _monitor_agent(self, task_id: str):
        """Monitor agent and send progress updates"""
        agent_info = self.running_agents.get(task_id)
        if not agent_info:
            return

        process = agent_info["process"]
        callback = agent_info["callback"]
        progress_callback = agent_info.get("progress_callback")
        task_name = agent_info["task_name"]

        # Progress update interval (every 60 seconds)
        update_interval = 60
        last_update = datetime.now()

        try:
            while True:
                # Check if process finished
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=update_interval
                    )
                    # Process finished
                    output = stdout.decode() if stdout else ""
                    errors = stderr.decode() if stderr else ""
                    result = output or errors or "No output"

                    if len(result) > 3500:
                        result = result[:1500] + "\n\n...[truncated]...\n\n" + result[-1500:]

                    success = process.returncode == 0

                    task_file = agent_info["task_file"]
                    if success and task_file.exists():
                        task_file.unlink()

                    await callback(task_id, task_name, success, result)
                    break

                except asyncio.TimeoutError:
                    # Process still running - send progress update
                    elapsed = datetime.now() - agent_info["started"]
                    elapsed_str = str(elapsed).split('.')[0]

                    if progress_callback and (datetime.now() - last_update).seconds >= update_interval:
                        await progress_callback(task_id, task_name, elapsed_str)
                        last_update = datetime.now()

                    # Check total timeout (10 min)
                    if elapsed.total_seconds() > 600:
                        process.kill()
                        await callback(task_id, task_name, False, "⏰ Timeout (10 min)")
                        break

        except Exception as e:
            await callback(task_id, task_name, False, str(e))

        finally:
            async with self.lock:
                self.running_agents.pop(task_id, None)

    def get_running_tasks(self) -> list:
        """Get list of running tasks"""
        result = []
        for task_id, info in self.running_agents.items():
            elapsed = datetime.now() - info["started"]
            result.append({
                "id": task_id,
                "name": info["task_name"],
                "elapsed": str(elapsed).split('.')[0]
            })
        return result


# Global agent manager
agent_manager = AgentManager(MAX_CONCURRENT_AGENTS)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_ID


def get_task_title(task_path: Path) -> str:
    """Extract human-readable title from task file"""
    try:
        content = task_path.read_text(encoding='utf-8')
        for line in content.strip().split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                # Remove emoji and common prefixes
                for prefix in ['🔍 ', '🔧 ', '🚀 ', '📋 ', '✅ ', '⚡ ', '🎯 ',
                              'AGENT TASK:', 'AGENT_TASK:', 'TASK:']:
                    title = title.replace(prefix, '').strip()
                return title[:50]  # Limit length for buttons
    except:
        pass
    return task_path.stem.replace("TASK_", "").replace("_", " ")[:50]


def get_persistent_keyboard() -> ReplyKeyboardMarkup:
    """Create persistent keyboard at bottom of chat"""
    keyboard = [
        [KeyboardButton("🚀 Start")],
        [KeyboardButton("🎯 Exec"), KeyboardButton("📋 Tasks"), KeyboardButton("📊 Status")],
        [KeyboardButton("🔬 Lab"), KeyboardButton("📝 Todo"), KeyboardButton("📚 Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_tasks_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """Create task selection keyboard"""
    keyboard = []

    # Add task buttons (up to 10)
    for i, task in enumerate(tasks[:10], 1):
        title = get_task_title(task)
        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1]
        keyboard.append([
            InlineKeyboardButton(f"{emoji} {title}", callback_data=f"exec_{i}")
        ])

    # Add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Отмена", callback_data="exec_cancel")
    ])

    return InlineKeyboardMarkup(keyboard)


# =============================================================================
# GITHUB INTEGRATION
# =============================================================================
async def create_github_issue(title: str, body: str = "", labels: list = None) -> dict:
    """Create GitHub Issue via API"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": title,
        "body": body or f"Created via EL_Bot at {datetime.now().isoformat()}",
        "labels": labels or ["from-bot"]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(GITHUB_API, json=data, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_github_issues(limit: int = 5) -> list:
    """Get recent GitHub Issues"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GITHUB_API, headers=headers,
            params={"state": "open", "per_page": limit, "sort": "created", "direction": "desc"}
        )
        response.raise_for_status()
        return response.json()


async def add_issue_to_project(issue_node_id: str) -> dict:
    """Add issue to GitHub Project V2"""
    headers = {
        "Authorization": f"bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    add_query = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item { id }
      }
    }
    """
    add_data = {
        "query": add_query,
        "variables": {"projectId": GITHUB_PROJECT_ID, "contentId": issue_node_id}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.github.com/graphql",
            json=add_data, headers=headers
        )
        result = response.json()

        if "errors" in result:
            raise Exception(result["errors"][0]["message"])

        item_id = result["data"]["addProjectV2ItemById"]["item"]["id"]

        # Set Status to "Todo"
        update_query = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
          updateProjectV2ItemFieldValue(input: {projectId: $projectId, itemId: $itemId, fieldId: $fieldId, value: $value}) {
            projectV2Item { id }
          }
        }
        """
        update_data = {
            "query": update_query,
            "variables": {
                "projectId": GITHUB_PROJECT_ID,
                "itemId": item_id,
                "fieldId": "PVTSSF_lAHOAoshms4BJvBCzg5z24I",
                "value": {"singleSelectOptionId": "f75ad846"}
            }
        }
        await client.post("https://api.github.com/graphql", json=update_data, headers=headers)
        return result


# =============================================================================
# COMMAND HANDLERS
# =============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show main menu with persistent keyboard"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("Access denied")
        logger.warning(f"Unauthorized: {user.id} ({user.username})")
        return

    status = agent_manager.get_status()

    # Send message with persistent keyboard
    await update.message.reply_text(
        f"🤖 EL_Bot v5.4\n\n"
        f"Привет, {user.first_name}!\n\n"
        f"📊 Агенты: {status}\n"
        f"📂 Репо: {GITHUB_REPO}\n\n"
        f"Кнопки закреплены внизу 👇",
        reply_markup=get_persistent_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - detailed help"""
    if not is_admin(update.effective_user.id):
        return

    help_text = """📚 EL_Bot v5 - Справка

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
/lab - Статус сервера
/status - Статус запущенных агентов

━━━ ℹ️ Прочее ━━━
/start - Главное меню
/help - Эта справка

━━━ ⚡ Агенты ━━━
Максимум параллельных: """ + str(MAX_CONCURRENT_AGENTS)

    await update.message.reply_text(help_text)


async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /exec command - show task selection"""
    if not is_admin(update.effective_user.id):
        return

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = sorted(TASKS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not tasks:
        await update.message.reply_text(
            "📭 Очередь задач пуста\n\n"
            "Отправьте .md файл чтобы добавить задачу"
        )
        return

    # Check if we can start new agent
    if not agent_manager.can_start_new():
        running = agent_manager.get_running_tasks()
        text = f"⏳ Все {MAX_CONCURRENT_AGENTS} агента заняты:\n\n"
        for task in running:
            text += f"• {task['name']} ({task['elapsed']})\n"
        text += "\nДождитесь завершения или добавьте задачу в очередь"
        await update.message.reply_text(text)
        return

    # Store tasks in context for callback
    context.user_data['pending_tasks'] = tasks

    await update.message.reply_text(
        f"📋 Выберите задачу ({len(tasks)} в очереди):",
        reply_markup=get_tasks_keyboard(tasks)
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tasks command - list queued tasks"""
    if not is_admin(update.effective_user.id):
        return

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = sorted(TASKS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not tasks:
        await update.message.reply_text("📭 Очередь задач пуста")
        return

    text = f"📋 Задачи в очереди ({len(tasks)}):\n\n"
    for i, task in enumerate(tasks[:15], 1):
        title = get_task_title(task)
        mtime = datetime.fromtimestamp(task.stat().st_mtime).strftime("%d.%m %H:%M")
        text += f"{i}. {title}\n   📅 {mtime}\n\n"

    if len(tasks) > 15:
        text += f"... и ещё {len(tasks) - 15}"

    await update.message.reply_text(text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show running agents"""
    if not is_admin(update.effective_user.id):
        return

    running = agent_manager.get_running_tasks()
    queued = len(list(TASKS_DIR.glob("*.md"))) if TASKS_DIR.exists() else 0

    if not running:
        text = f"📊 Статус агентов\n\n"
        text += f"💤 Нет активных задач\n"
        text += f"📋 В очереди: {queued}\n"
        text += f"⚡ Доступно слотов: {MAX_CONCURRENT_AGENTS}"
    else:
        text = f"📊 Статус агентов ({len(running)}/{MAX_CONCURRENT_AGENTS})\n\n"
        for task in running:
            text += f"🔄 {task['name']}\n"
            text += f"   ⏱ {task['elapsed']}\n\n"
        text += f"📋 В очереди: {queued}"

    await update.message.reply_text(text)


async def lab_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /lab command - local server monitoring"""
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text("🔬 Проверяю сервисы...")

    checks = []
    problems = []

    # Check CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_status = "✅" if cpu_percent < 80 else "⚠️"
    checks.append(f"{cpu_status} CPU: {cpu_percent}%")
    if cpu_percent >= 80:
        problems.append("🔧 CPU: Высокая нагрузка")

    # Check Memory
    mem = psutil.virtual_memory()
    mem_status = "✅" if mem.percent < 85 else "⚠️"
    checks.append(f"{mem_status} RAM: {mem.percent}% ({mem.used // 1024 // 1024}MB / {mem.total // 1024 // 1024}MB)")
    if mem.percent >= 85:
        problems.append("🔧 RAM: Мало памяти")

    # Check Disk
    disk = psutil.disk_usage('/')
    disk_status = "✅" if disk.percent < 90 else "⚠️"
    checks.append(f"{disk_status} Disk: {disk.percent}% ({disk.free // 1024 // 1024 // 1024}GB free)")
    if disk.percent >= 90:
        problems.append("🔧 Disk: Мало места")

    # Check Claude CLI
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.communicate(), timeout=5)
        checks.append("✅ Claude CLI: installed")
    except:
        checks.append("❌ Claude CLI: not found")
        problems.append("🔧 Claude CLI: npm install -g @anthropic-ai/claude-code")

    # Check Node.js
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        version = stdout.decode().strip()
        checks.append(f"✅ Node.js: {version}")
    except:
        checks.append("❌ Node.js: not found")
        problems.append("🔧 Node.js: apt install nodejs")

    # Check Agents
    running_count = agent_manager.get_running_count()
    checks.append(f"✅ Agents: {running_count}/{MAX_CONCURRENT_AGENTS} active")

    # Check Tasks queue
    tasks_count = len(list(TASKS_DIR.glob("*.md"))) if TASKS_DIR.exists() else 0
    checks.append(f"✅ Tasks queue: {tasks_count}")

    # Build response
    timestamp = datetime.now().strftime("%H:%M:%S")

    if problems:
        header = "⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ"
    else:
        header = "✅ ВСЁ РАБОТАЕТ ШТАТНО"

    text = f"🔬 LAB Status\n\n{header}\n\n━━━ Сервисы ━━━\n"
    text += "\n".join(checks)

    if problems:
        text += "\n\n━━━ Рекомендации ━━━\n"
        text += "\n".join(problems)

    text += f"\n\n🕐 Проверено: {timestamp}"

    await update.message.reply_text(text)


async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command - clear task queue"""
    if not is_admin(update.effective_user.id):
        return

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = list(TASKS_DIR.glob("*.md"))
    count = len(tasks)

    for task in tasks:
        task.unlink()

    await update.message.reply_text(f"🗑 Удалено задач: {count}")
    logger.info(f"Cleared {count} tasks")


async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /todo command - create GitHub Issue"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access denied")
        return

    if not context.args:
        await update.message.reply_text("❌ Укажи текст:\n/todo Добавить валидацию")
        return

    text = " ".join(context.args)
    title, body = (text.split("|", 1) + [""])[:2]
    title, body = title.strip(), body.strip()

    try:
        await update.message.reply_text("⏳ Создаю Issue...")
        issue = await create_github_issue(title, body)
        await update.message.reply_text(
            f"✅ Issue #{issue['number']} создан!\n\n"
            f"📋 {issue['title']}\n"
            f"🔗 {issue['html_url']}"
        )
        logger.info(f"Created issue #{issue['number']}: {title}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def list_issues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list command - show recent Issues"""
    if not is_admin(update.effective_user.id):
        return

    try:
        issues = await get_github_issues(5)
        if not issues:
            await update.message.reply_text("📭 Нет открытых Issues")
            return

        text = "📋 Последние Issues:\n\n"
        for issue in issues:
            labels = ", ".join([l["name"] for l in issue.get("labels", [])])
            label_str = f" [{labels}]" if labels else ""
            text += f"• #{issue['number']}{label_str}\n  {issue['title']}\n\n"

        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


# =============================================================================
# CALLBACK HANDLERS
# =============================================================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    data = query.data

    # Menu buttons
    if data == "menu_exec":
        await exec_callback(query, context)
    elif data == "menu_tasks":
        await tasks_callback(query, context)
    elif data == "menu_status":
        await status_callback(query, context)
    elif data == "menu_lab":
        await lab_callback(query, context)
    elif data == "menu_todo":
        await query.edit_message_text(
            "📝 Создание Issue\n\n"
            "Отправьте текст или используйте:\n"
            "/todo Заголовок | Описание"
        )
    elif data == "menu_help":
        await help_callback(query, context)

    # Exec task selection
    elif data.startswith("exec_"):
        await handle_exec_callback(query, context, data)


async def exec_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle exec menu button"""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = sorted(TASKS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not tasks:
        await query.edit_message_text(
            "📭 Очередь задач пуста\n\n"
            "Отправьте .md файл чтобы добавить задачу"
        )
        return

    if not agent_manager.can_start_new():
        running = agent_manager.get_running_tasks()
        text = f"⏳ Все {MAX_CONCURRENT_AGENTS} агента заняты:\n\n"
        for task in running:
            text += f"• {task['name']} ({task['elapsed']})\n"
        await query.edit_message_text(text)
        return

    context.user_data['pending_tasks'] = tasks

    await query.edit_message_text(
        f"📋 Выберите задачу ({len(tasks)} в очереди):",
        reply_markup=get_tasks_keyboard(tasks)
    )


async def tasks_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tasks menu button"""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = sorted(TASKS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not tasks:
        await query.edit_message_text("📭 Очередь задач пуста")
        return

    text = f"📋 Задачи в очереди ({len(tasks)}):\n\n"
    for i, task in enumerate(tasks[:10], 1):
        title = get_task_title(task)
        mtime = datetime.fromtimestamp(task.stat().st_mtime).strftime("%d.%m %H:%M")
        text += f"{i}. {title}\n   📅 {mtime}\n\n"

    await query.edit_message_text(text)


async def status_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle status menu button"""
    running = agent_manager.get_running_tasks()
    queued = len(list(TASKS_DIR.glob("*.md"))) if TASKS_DIR.exists() else 0

    if not running:
        text = f"📊 Статус агентов\n\n"
        text += f"💤 Нет активных задач\n"
        text += f"📋 В очереди: {queued}\n"
        text += f"⚡ Доступно слотов: {MAX_CONCURRENT_AGENTS}"
    else:
        text = f"📊 Статус агентов ({len(running)}/{MAX_CONCURRENT_AGENTS})\n\n"
        for task in running:
            text += f"🔄 {task['name']}\n"
            text += f"   ⏱ {task['elapsed']}\n\n"
        text += f"📋 В очереди: {queued}"

    await query.edit_message_text(text)


async def lab_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle lab menu button"""
    await query.edit_message_text("🔬 Проверяю сервисы...")

    # Simplified check for callback (full check in command)
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    running_count = agent_manager.get_running_count()
    tasks_count = len(list(TASKS_DIR.glob("*.md"))) if TASKS_DIR.exists() else 0

    status = "✅ ВСЁ ОК" if cpu_percent < 80 and mem.percent < 85 else "⚠️ ВНИМАНИЕ"
    timestamp = datetime.now().strftime("%H:%M:%S")

    text = f"🔬 LAB Status\n\n{status}\n\n"
    text += f"{'✅' if cpu_percent < 80 else '⚠️'} CPU: {cpu_percent}%\n"
    text += f"{'✅' if mem.percent < 85 else '⚠️'} RAM: {mem.percent}%\n"
    text += f"✅ Agents: {running_count}/{MAX_CONCURRENT_AGENTS}\n"
    text += f"✅ Queue: {tasks_count}\n\n"
    text += f"🕐 {timestamp}"

    await query.edit_message_text(text)


async def help_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help menu button"""
    help_text = """📚 EL_Bot v5 - Справка

🚀 /exec - Запустить задачу
📋 /tasks - Очередь задач
📊 /status - Статус агентов
🔬 /lab - Мониторинг сервера
📝 /todo - Создать Issue
📜 /list - Последние Issues
🗑 /clear - Очистить очередь

📎 Отправь .md файл → добавить задачу
💬 Просто текст → создать Issue

⚡ Макс. параллельных агентов: """ + str(MAX_CONCURRENT_AGENTS)

    await query.edit_message_text(help_text)


async def handle_exec_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    """Handle task execution callback"""
    if data == "exec_cancel":
        await query.edit_message_text("❌ Отменено")
        return

    # Get task number
    try:
        task_num = int(data.replace("exec_", "")) - 1
    except:
        await query.edit_message_text("❌ Ошибка выбора")
        return

    tasks = context.user_data.get('pending_tasks', [])
    if not tasks or task_num >= len(tasks):
        await query.edit_message_text("❌ Задача не найдена")
        return

    task_file = tasks[task_num]
    task_name = get_task_title(task_file)
    task_id = f"{task_file.stem}_{datetime.now().strftime('%H%M%S')}"

    # Create callbacks for notifications
    bot = context.bot
    chat_id = query.message.chat_id

    async def on_complete(tid: str, name: str, success: bool, result: str):
        emoji = "✅" if success else "❌"
        status = "ЗАВЕРШЕНО" if success else "ОШИБКА"
        logger.info(f"Agent completed: {name}, success={success}, result_len={len(result)}")
        text = f"{emoji} АГЕНТ {status}\n\n📋 Задача: {name}\n\n📝 Результат:\n{result}"
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            logger.info(f"Completion notification sent for {name}")
        except Exception as e:
            logger.error(f"Failed to send completion notification: {e}")

    async def on_progress(tid: str, name: str, elapsed: str):
        text = f"⏳ Агент работает: {name}\n\n⏱ Время: {elapsed}\n📊 Статус: в процессе..."
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            logger.info(f"Progress update sent for {name}: {elapsed}")
        except Exception as e:
            logger.error(f"Failed to send progress notification: {e}")

    # Start agent with progress callback
    started = await agent_manager.start_agent(task_id, task_name, task_file, on_complete, on_progress)

    if started:
        running = agent_manager.get_running_count()
        await query.edit_message_text(
            f"🚀 Запущено: {task_name}\n\n"
            f"📊 Агентов: {running}/{MAX_CONCURRENT_AGENTS}\n"
            f"⏳ Ожидайте уведомление..."
        )
    else:
        await query.edit_message_text(
            f"❌ Не удалось запустить агента\n"
            f"Все слоты заняты"
        )


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document upload - add task"""
    if not is_admin(update.effective_user.id):
        return

    document = update.message.document
    if not document:
        return

    filename = document.file_name or "unknown.md"
    if not filename.endswith(".md"):
        await update.message.reply_text(f"❌ Только .md файлы\nПолучен: {filename}")
        return

    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        content = file_bytes.decode('utf-8')

        # Generate unique task ID
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = filename.replace(" ", "_")
        task_filename = f"TASK_{task_id}_{safe_name}"

        # Save file
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = TASKS_DIR / task_filename
        filepath.write_text(content, encoding='utf-8')

        # Extract title
        title = get_task_title(filepath)

        # Create GitHub Issue
        await update.message.reply_text("⏳ Создаю Issue...")
        body = f"📁 `{task_filename}`"
        issue = await create_github_issue(title=title, body=body, labels=["task"])

        # Add to project
        issue_node_id = issue.get("node_id")
        if issue_node_id:
            try:
                await add_issue_to_project(issue_node_id)
            except Exception as e:
                logger.error(f"Failed to add to project: {e}")

        tasks_count = len(list(TASKS_DIR.glob("*.md")))

        # Create inline button to run exec
        exec_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Запустить", callback_data="menu_exec")]
        ])

        await update.message.reply_text(
            f"✅ Задача добавлена!\n\n"
            f"📋 {title}\n"
            f"🔗 Issue #{issue['number']}\n"
            f"📊 В очереди: {tasks_count}",
            reply_markup=exec_keyboard
        )
        logger.info(f"Created task: {task_filename}")

    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle persistent keyboard button presses"""
    if not is_admin(update.effective_user.id):
        return

    text = update.message.text.strip()

    # Map button text to actions
    if text == "🚀 Start":
        await start(update, context)
    elif text == "🎯 Exec":
        await exec_command(update, context)
    elif text == "📋 Tasks":
        await tasks_command(update, context)
    elif text == "📊 Status":
        await status_command(update, context)
    elif text == "🔬 Lab":
        await lab_command(update, context)
    elif text == "📝 Todo":
        await update.message.reply_text(
            "📝 Создание Issue\n\n"
            "Отправьте текст или используйте:\n"
            "/todo Заголовок | Описание"
        )
    elif text == "📚 Help":
        await help_command(update, context)
    else:
        # Not a button - treat as quick todo
        await quick_todo_text(update, context, text)


async def quick_todo_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Create GitHub Issue from text"""
    title, body = (text.split("|", 1) + [""])[:2]
    title, body = title.strip(), body.strip()

    try:
        issue = await create_github_issue(title, body)
        await update.message.reply_text(
            f"✅ #{issue['number']}: {issue['title']}\n"
            f"🔗 {issue['html_url']}"
        )
        logger.info(f"Quick issue #{issue['number']}: {title}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"❌ {e}")


async def quick_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text - route to keyboard handler or create Issue"""
    if not is_admin(update.effective_user.id):
        return

    text = update.message.text.strip()
    if not text or text.startswith("/"):
        return

    # Check if it's a keyboard button
    keyboard_buttons = ["🚀 Start", "🎯 Exec", "📋 Tasks", "📊 Status", "🔬 Lab", "📝 Todo", "📚 Help"]
    if text in keyboard_buttons:
        await handle_keyboard_buttons(update, context)
    else:
        await quick_todo_text(update, context, text)


# =============================================================================
# INITIALIZATION
# =============================================================================
async def post_init(application: Application) -> None:
    """Set bot commands after init"""
    commands = [
        BotCommand("start", "Главное меню"),
        BotCommand("exec", "Запустить задачу"),
        BotCommand("tasks", "Очередь задач"),
        BotCommand("status", "Статус агентов"),
        BotCommand("lab", "Мониторинг сервера"),
        BotCommand("todo", "Создать Issue"),
        BotCommand("list", "Последние Issues"),
        BotCommand("clear", "Очистить очередь"),
        BotCommand("help", "Справка"),
    ]
    await application.bot.set_my_commands(commands)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Tasks directory: {TASKS_DIR}")
    logger.info(f"Max concurrent agents: {MAX_CONCURRENT_AGENTS}")


def main() -> None:
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set!")
    if not ADMIN_ID:
        raise ValueError("TELEGRAM_ADMIN_ID not set!")

    logger.info(f"Starting EL_Bot v5 for {GITHUB_REPO}")
    logger.info(f"Admin ID: {ADMIN_ID}")
    logger.info(f"Tasks dir: {TASKS_DIR}")
    logger.info(f"Project dir: {PROJECT_DIR}")
    logger.info(f"Max agents: {MAX_CONCURRENT_AGENTS}")

    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("exec", exec_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("lab", lab_command))
    app.add_handler(CommandHandler("todo", todo))
    app.add_handler(CommandHandler("list", list_issues))
    app.add_handler(CommandHandler("clear", clear_tasks))

    # Callback handler for buttons
    app.add_handler(CallbackQueryHandler(button_callback))

    # Message handlers
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_todo))

    # Start polling
    logger.info("Bot v5.4 started! (shell pipe for claude)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
