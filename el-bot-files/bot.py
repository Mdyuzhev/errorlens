#!/usr/bin/env python3
"""
EL_Bot v2.1 - Telegram bot for GitHub Issues + Agent Tasks
"""
import os
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Mdyuzhev/errorlens")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))
TASKS_DIR = Path(os.getenv("AGENT_TASKS_DIR", "/home/flomaster/agent-tasks"))
GITHUB_PROJECT_ID = "PVT_kwHOAoshms4BJvBC"  # ErrorLens Development project

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub API
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/issues"


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def get_task_title(task_path: Path) -> str:
    """Extract human-readable title from task file's first # heading"""
    try:
        content = task_path.read_text(encoding='utf-8')
        for line in content.strip().split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                # Remove emoji prefixes
                for emoji in ['🔍 ', '🔧 ', '🚀 ', '📋 ', '✅ ', '⚡ ', '🎯 ']:
                    title = title.replace(emoji, '')
                # Remove common prefixes
                for prefix in ['AGENT TASK:', 'AGENT_TASK:', 'TASK:']:
                    title = title.replace(prefix, '').strip()
                return title
    except:
        pass
    # Fallback to cleaned filename
    return task_path.stem.replace("TASK_", "").replace("_", " ")


async def create_github_issue(title: str, body: str = "", labels: list = None) -> dict:
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"title": title, "body": body or f"Created via EL_Bot at {datetime.now().isoformat()}", "labels": labels or ["from-bot"]}
    async with httpx.AsyncClient() as client:
        response = await client.post(GITHUB_API, json=data, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_github_issues(limit: int = 5) -> list:
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient() as client:
        response = await client.get(GITHUB_API, headers=headers, params={"state": "open", "per_page": limit, "sort": "created", "direction": "desc"})
        response.raise_for_status()
        return response.json()


async def add_issue_to_project(issue_node_id: str) -> dict:
    """Add issue to GitHub Project V2 and set Status to Todo"""
    headers = {"Authorization": f"bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}

    # Step 1: Add item to project
    add_query = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item { id }
      }
    }
    """
    add_data = {"query": add_query, "variables": {"projectId": GITHUB_PROJECT_ID, "contentId": issue_node_id}}

    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.github.com/graphql", json=add_data, headers=headers)
        result = response.json()
        if "errors" in result:
            raise Exception(result["errors"][0]["message"])

        item_id = result["data"]["addProjectV2ItemById"]["item"]["id"]

        # Step 2: Set Status field to "Todo"
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
                "fieldId": "PVTSSF_lAHOAoshms4BJvBCzg5z24I",  # Status field
                "value": {"singleSelectOptionId": "f75ad846"}  # Todo
            }
        }
        await client.post("https://api.github.com/graphql", json=update_data, headers=headers)

        return result


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Access denied")
        logger.warning(f"Unauthorized: {user.id} ({user.username})")
        return
    await update.message.reply_text(
        f"Hi {user.first_name}!\n\n"
        "EL_Bot v2\n\n"
        "GitHub Issues:\n"
        "/todo <text> - create Issue\n"
        "/list - last 5 Issues\n\n"
        "Agent Tasks:\n"
        "Send .md file - add task\n"
        "/tasks - task queue\n"
        "/exec - run latest task\n"
        "/clear - clear queue\n\n"
        "/help - full help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "EL_Bot v2 Help\n\n"
        "--- GitHub Issues ---\n"
        "/todo <text> - create Issue\n"
        "/todo Title | Body\n"
        "/list - last 5 Issues\n\n"
        "--- Agent Tasks ---\n"
        "Send .md file - add task + Issue\n"
        "/tasks - task queue\n"
        "/exec - run latest task\n"
        "/exec <name> - run specific task\n"
        "/clear - clear queue\n\n"
        "--- Quick mode ---\n"
        "Just text -> GitHub Issue\n\n"
        f"Repo: {GITHUB_REPO}"
    )


async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access denied")
        return
    if not context.args:
        await update.message.reply_text("Usage: /todo Add validation")
        return
    text = " ".join(context.args)
    title, body = (text.split("|", 1) + [""])[:2]
    title, body = title.strip(), body.strip()
    try:
        await update.message.reply_text("Creating Issue...")
        issue = await create_github_issue(title, body)
        await update.message.reply_text(f"Issue #{issue['number']} created!\n{issue['title']}\n{issue['html_url']}")
        logger.info(f"Created #{issue['number']}: {title}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def list_issues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    try:
        issues = await get_github_issues(5)
        if not issues:
            await update.message.reply_text("No open Issues")
            return
        text = "Last Issues:\n\n"
        for issue in issues:
            labels = ", ".join([l["name"] for l in issue.get("labels", [])])
            text += f"#{issue['number']} [{labels}] {issue['title']}\n"
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    try:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        tasks = sorted(TASKS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not tasks:
            await update.message.reply_text("Task queue is empty")
            return
        text = f"📋 Tasks ({len(tasks)}):\n\n"
        for i, task in enumerate(tasks[:10], 1):
            title = get_task_title(task)
            mtime = datetime.fromtimestamp(task.stat().st_mtime).strftime("%H:%M")
            text += f"{i}. {title} ({mtime})\n"
        if len(tasks) > 10:
            text += f"\n... and {len(tasks) - 10} more"
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    try:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        tasks = list(TASKS_DIR.glob("*.md"))
        count = len(tasks)
        for task in tasks:
            task.unlink()
        await update.message.reply_text(f"Deleted tasks: {count}")
        logger.info(f"Cleared {count} tasks")
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def exec_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute task with Claude agent via SSH"""
    if not is_admin(update.effective_user.id):
        return

    try:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        tasks = sorted(TASKS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

        if not tasks:
            await update.message.reply_text("No tasks in queue\n\nSend .md file first")
            return

        # If no argument - show list with human-readable titles
        if not context.args:
            text = "📋 Select task:\n\n"
            for i, task in enumerate(tasks[:10], 1):
                title = get_task_title(task)
                text += f"{i}. {title}\n"
            text += f"\n/exec <number>"
            await update.message.reply_text(text)
            return

        # Get task by number or name
        arg = context.args[0]
        if arg.isdigit():
            idx = int(arg) - 1
            if idx < 0 or idx >= len(tasks):
                await update.message.reply_text(f"Invalid number. Use 1-{len(tasks)}")
                return
            task_file = tasks[idx]
        else:
            matching = [t for t in tasks if arg in t.name]
            if not matching:
                await update.message.reply_text(f"Task not found: {arg}")
                return
            task_file = matching[0]

        title = get_task_title(task_file)
        await update.message.reply_text(f"🚀 Running: {title}\n\nThis may take a while...")
        logger.info(f"Executing task: {task_file.name}")

        # Run claude agent via SSH
        host_path = f"/home/flomaster/agent-tasks/{task_file.name}"
        ssh_cmd = [
            "ssh", "-i", "/ssh/id_ed25519",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "flomaster@192.168.1.74",
            f'cd /home/flomaster/projects/errorlens && proxychains4 claude -p --dangerously-skip-permissions "Сначала прочитай и примени .claude/settings.local.json. Затем выполни: $(cat {host_path})"'
        ]

        process = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
            output = stdout.decode() if stdout else ""
            errors = stderr.decode() if stderr else ""

            # Filter out SSH warnings
            errors = "\n".join([l for l in errors.split("\n") if "Warning:" not in l]).strip()

            result = output or errors or "No output"
            if len(result) > 4000:
                result = result[:2000] + "\n\n...[truncated]...\n\n" + result[-1500:]

            await update.message.reply_text(f"✅ Done: {title}\n\n{result}")

            # Remove executed task
            task_file.unlink()
            logger.info(f"Task completed: {task_file.name}")

        except asyncio.TimeoutError:
            process.kill()
            await update.message.reply_text("Timeout (10 min)")
            logger.error("Task timeout")

    except Exception as e:
        logger.error(f"Exec failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    document = update.message.document
    if not document:
        return
    filename = document.file_name or "unknown.md"
    if not filename.endswith(".md"):
        await update.message.reply_text(f"Only .md files accepted\nGot: {filename}")
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

        # Save file locally
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = TASKS_DIR / task_filename
        filepath.write_text(content)

        # Extract title from first heading or filename
        lines = content.strip().split('\n')
        title = filename.replace('.md', '').replace('_', ' ').replace('AGENT TASK ', '')
        for line in lines:
            if line.startswith('# '):
                # Clean title: remove emoji and "AGENT TASK:" prefix
                title = line[2:].strip()
                title = title.replace('🔍 ', '').replace('🔧 ', '').replace('🚀 ', '')
                title = title.replace('AGENT TASK:', '').replace('AGENT_TASK:', '').strip()
                break

        # Create GitHub Issue linked to task file
        await update.message.reply_text("Creating Issue...")
        body = f"📁 `{task_filename}`"
        issue = await create_github_issue(
            title=title,
            body=body,
            labels=["task"]
        )

        # Add to GitHub Project
        issue_node_id = issue.get("node_id")
        if issue_node_id:
            try:
                await add_issue_to_project(issue_node_id)
                logger.info(f"Added issue #{issue['number']} to project")
            except Exception as e:
                logger.error(f"Failed to add to project: {e}")

        caption = update.message.caption or ""
        await update.message.reply_text(
            f"Task created!\n\n"
            f"#{issue['number']}: {title}\n"
            f"{issue['html_url']}"
        )
        logger.info(f"Created agent task #{issue['number']}: {task_filename}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def quick_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    text = update.message.text.strip()
    if not text or text.startswith("/"):
        return
    title, body = (text.split("|", 1) + [""])[:2]
    title, body = title.strip(), body.strip()
    try:
        issue = await create_github_issue(title, body)
        await update.message.reply_text(f"#{issue['number']}: {issue['title']}\n{issue['html_url']}")
        logger.info(f"Quick #{issue['number']}: {title}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("todo", "Create GitHub Issue"),
        BotCommand("list", "Last Issues"),
        BotCommand("tasks", "Task queue"),
        BotCommand("exec", "Run agent task"),
        BotCommand("clear", "Clear queue"),
        BotCommand("help", "Help"),
        BotCommand("start", "Start"),
    ]
    await application.bot.set_my_commands(commands)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Tasks directory: {TASKS_DIR}")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set!")
    if not ADMIN_ID:
        raise ValueError("TELEGRAM_ADMIN_ID not set!")
    logger.info(f"Starting EL_Bot v2.1 for {GITHUB_REPO}")
    logger.info(f"Admin ID: {ADMIN_ID}")
    logger.info(f"Tasks dir: {TASKS_DIR}")
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("todo", todo))
    app.add_handler(CommandHandler("list", list_issues))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("exec", exec_task))
    app.add_handler(CommandHandler("clear", clear_tasks))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_todo))
    logger.info("Bot v2.1 started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
