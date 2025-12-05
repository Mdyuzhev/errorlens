#!/usr/bin/env python3
"""
EL_Bot v3 - Telegram bot for GitHub Issues + Agent Tasks
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
GITHUB_PROJECT_ID = "PVT_kwHOAoshms4BJvBC"

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub API
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/issues"


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


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
    headers = {"Authorization": f"bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Access denied")
        logger.warning(f"Unauthorized: {user.id} ({user.username})")
        return
    await update.message.reply_text(
        f"Hi {user.first_name}!\n\n"
        "EL_Bot v3\n\n"
        "/todo <text> - create Issue\n"
        "/list - last 5 Issues\n"
        "/tasks - task queue\n"
        "/exec - run task\n"
        "/update - pull repo\n"
        "/clear - clear queue\n"
        "/help - full help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "EL_Bot v3 Help\n\n"
        "/todo <text> - create Issue\n"
        "/list - last 5 Issues\n"
        "/tasks - task queue\n"
        "/exec - show tasks\n"
        "/exec <num> - run task\n"
        "/update - pull from GitHub\n"
        "/clear - clear queue\n\n"
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
        await update.message.reply_text(f"Issue #{issue['number']} created!\n{issue['html_url']}")
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
        text = f"Tasks ({len(tasks)}):\n\n"
        for i, task in enumerate(tasks[:10], 1):
            name = task.name.replace("TASK_", "").replace(".md", "")
            text += f"{i}. {name}\n"
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
        await update.message.reply_text(f"Deleted: {count}")
        logger.info(f"Cleared {count} tasks")
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def update_repo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    try:
        await update.message.reply_text("Updating...")
        ssh_cmd = [
            "ssh", "-i", "/ssh/id_ed25519",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "flomaster@192.168.1.74",
            "/home/flomaster/projects/update-errorlens.sh"
        ]
        process = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        output = stdout.decode().strip() if stdout else ""
        if process.returncode == 0 and output:
            await update.message.reply_text("Updated!\n\n" + output)
            logger.info("Repo updated: " + output)
        else:
            errors = stderr.decode().strip() if stderr else "Unknown error"
            await update.message.reply_text("Failed:\n" + errors[:500])
            logger.error("Update failed: " + errors)
    except asyncio.TimeoutError:
        await update.message.reply_text("Timeout (60s)")
    except Exception as e:
        logger.error("Update failed: " + str(e))
        await update.message.reply_text("Error: " + str(e))


async def exec_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    try:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        tasks = sorted(TASKS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not tasks:
            await update.message.reply_text("No tasks. Send .md file first")
            return
        if not context.args:
            text = "Select task:\n\n"
            for i, task in enumerate(tasks[:10], 1):
                # Extract title from first # heading in file
                title = task.name.replace("TASK_", "").replace(".md", "")
                try:
                    content = task.read_text()[:500]
                    for line in content.split('\n'):
                        if line.startswith('# '):
                            title = line[2:].strip()[:50]
                            break
                except:
                    pass
                text += f"{i}. {title}\n"
            text += "
Ответь номером:"
            await update.message.reply_text(text)
            return
        arg = context.args[0]
        if arg.isdigit():
            idx = int(arg) - 1
            if idx < 0 or idx >= len(tasks):
                await update.message.reply_text(f"Invalid. Use 1-{len(tasks)}")
                return
            task_file = tasks[idx]
        else:
            matching = [t for t in tasks if arg in t.name]
            if not matching:
                await update.message.reply_text(f"Not found: {arg}")
                return
            task_file = matching[0]
        await update.message.reply_text(f"Running: {task_file.name}\n\nPlease wait...")
        logger.info(f"Executing: {task_file.name}")
        host_path = f"/home/flomaster/agent-tasks/{task_file.name}"
        cmd_str = f'cd /home/flomaster/projects/errorlens && proxychains4 claude-vpn -d -p "Сначала прочитай и примени .claude/settings.local.json. Затем выполни: $(cat {host_path})"'
        ssh_cmd = [
            "ssh", "-i", "/ssh/id_ed25519",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "flomaster@192.168.1.74",
            cmd_str
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
            errors = "\n".join([l for l in errors.split("\n") if "Warning:" not in l and "proxychains" not in l.lower()]).strip()
            result = output or errors or "No output"
            if len(result) > 4000:
                result = result[:2000] + "\n\n...[truncated]...\n\n" + result[-1500:]
            await update.message.reply_text("Done!\n\n" + result)
            task_file.unlink()
            logger.info(f"Completed: {task_file.name}")
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
        await update.message.reply_text(f"Only .md files\nGot: {filename}")
        return
    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        content = file_bytes.decode('utf-8')
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = filename.replace(" ", "_")
        task_filename = f"TASK_{task_id}_{safe_name}"
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = TASKS_DIR / task_filename
        filepath.write_text(content)
        lines = content.strip().split('\n')
        title = filename.replace('.md', '').replace('_', ' ')
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                for prefix in ['AGENT TASK:', 'AGENT_TASK:']:
                    title = title.replace(prefix, '').strip()
                break
        await update.message.reply_text("Creating Issue...")
        body = f"Task: {task_filename}"
        issue = await create_github_issue(title=title, body=body, labels=["task"])
        issue_node_id = issue.get("node_id")
        if issue_node_id:
            try:
                await add_issue_to_project(issue_node_id)
            except Exception as e:
                logger.error(f"Failed to add to project: {e}")
        await update.message.reply_text(f"Task created!\n#{issue['number']}: {title}\n{issue['html_url']}")
        logger.info(f"Created task #{issue['number']}: {task_filename}")
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
    except Exception as e:
        logger.error(f"Failed: {e}")
        await update.message.reply_text(f"Error: {e}")


async def post_init(application) -> None:
    commands = [
        BotCommand("todo", "Create Issue"),
        BotCommand("list", "Last Issues"),
        BotCommand("tasks", "Task queue"),
        BotCommand("exec", "Run task"),
        BotCommand("update", "Update repo"),
        BotCommand("clear", "Clear queue"),
        BotCommand("help", "Help"),
        BotCommand("start", "Start"),
    ]
    await application.bot.set_my_commands(commands)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Tasks: {TASKS_DIR}")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set!")
    if not ADMIN_ID:
        raise ValueError("TELEGRAM_ADMIN_ID not set!")
    logger.info(f"Starting EL_Bot v3 for {GITHUB_REPO}")
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("todo", todo))
    app.add_handler(CommandHandler("list", list_issues))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("exec", exec_task))
    app.add_handler(CommandHandler("update", update_repo))
    app.add_handler(CommandHandler("clear", clear_tasks))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_todo))
    logger.info("Bot v3 started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
