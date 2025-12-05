#!/bin/bash
# =============================================================================
# EL_Bot Deployment Script for K3s
# One script to rule them all! 🤖
# =============================================================================

set -e  # Exit on error

echo "🤖 EL_Bot Deployment Started!"
echo "================================"

# -----------------------------------------------------------------------------
# ШАГ 2: Create namespace
# -----------------------------------------------------------------------------
echo ""
echo "📦 ШАГ 2: Creating namespace 'bots'..."
kubectl create namespace bots 2>/dev/null || echo "  → Namespace 'bots' already exists"
kubectl get namespaces | grep bots

# -----------------------------------------------------------------------------
# ШАГ 3: Create project directory
# -----------------------------------------------------------------------------
echo ""
echo "📁 ШАГ 3: Creating project directory..."
mkdir -p ~/projects/bots/el-bot
cd ~/projects/bots/el-bot
echo "  → Working directory: $(pwd)"

# -----------------------------------------------------------------------------
# ШАГ 4: Create bot.py
# -----------------------------------------------------------------------------
echo ""
echo "🐍 ШАГ 4: Creating bot.py..."
cat > bot.py << 'BOTEOF'
#!/usr/bin/env python3
"""
EL_Bot - Telegram bot for creating GitHub Issues
"""
import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Mdyuzhev/errorlens")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# GitHub API
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/issues"


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_ID


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
            GITHUB_API,
            headers=headers,
            params={"state": "open", "per_page": limit, "sort": "created", "direction": "desc"}
        )
        response.raise_for_status()
        return response.json()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("⛔ Доступ запрещён")
        logger.warning(f"Unauthorized access attempt from {user.id} ({user.username})")
        return

    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Я EL_Bot — создаю задачи в GitHub.\n\n"
        "📋 Команды:\n"
        "/todo <текст> — создать Issue\n"
        "/list — последние 5 Issues\n"
        "/help — справка\n\n"
        "💡 Или просто напиши текст — создам Issue!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "📖 Справка EL_Bot\n\n"
        "Команды:\n"
        "• /todo <текст> — создать Issue\n"
        "• /todo <заголовок> | <описание> — с описанием\n"
        "• /list — последние 5 открытых Issues\n"
        "• /start — приветствие\n\n"
        "Быстрый режим:\n"
        "Просто напиши текст — создам Issue!\n\n"
        f"📂 Репозиторий: {GITHUB_REPO}"
    )


async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /todo command - create GitHub Issue"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Доступ запрещён")
        return

    if not context.args:
        await update.message.reply_text("❌ Укажи текст задачи:\n/todo Добавить валидацию")
        return

    text = " ".join(context.args)

    # Parse title | body
    if "|" in text:
        parts = text.split("|", 1)
        title = parts[0].strip()
        body = parts[1].strip()
    else:
        title = text
        body = ""

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
        logger.error(f"Failed to create issue: {e}")
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
        logger.error(f"Failed to list issues: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def quick_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any text message - quick Issue creation"""
    if not is_admin(update.effective_user.id):
        return

    text = update.message.text.strip()

    if not text or text.startswith("/"):
        return

    # Parse title | body
    if "|" in text:
        parts = text.split("|", 1)
        title = parts[0].strip()
        body = parts[1].strip()
    else:
        title = text
        body = ""

    try:
        issue = await create_github_issue(title, body)

        await update.message.reply_text(
            f"✅ #{issue['number']}: {issue['title']}\n"
            f"🔗 {issue['html_url']}"
        )
        logger.info(f"Quick created issue #{issue['number']}: {title}")

    except Exception as e:
        logger.error(f"Failed to create issue: {e}")
        await update.message.reply_text(f"❌ {e}")


async def post_init(application: Application) -> None:
    """Set bot commands after init"""
    commands = [
        BotCommand("todo", "Создать Issue"),
        BotCommand("list", "Последние 5 Issues"),
        BotCommand("help", "Справка"),
        BotCommand("start", "Начать"),
    ]
    await application.bot.set_my_commands(commands)


def main() -> None:
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set!")
    if not ADMIN_ID:
        raise ValueError("TELEGRAM_ADMIN_ID not set!")

    logger.info(f"Starting EL_Bot for repo {GITHUB_REPO}")
    logger.info(f"Admin ID: {ADMIN_ID}")

    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("todo", todo))
    app.add_handler(CommandHandler("list", list_issues))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_todo))

    # Start polling
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
BOTEOF
echo "  → bot.py created ($(wc -l < bot.py) lines)"

# -----------------------------------------------------------------------------
# ШАГ 5: Create requirements.txt
# -----------------------------------------------------------------------------
echo ""
echo "📋 ШАГ 5: Creating requirements.txt..."
cat > requirements.txt << 'EOF'
python-telegram-bot==21.3
httpx==0.27.0
EOF
echo "  → requirements.txt created"

# -----------------------------------------------------------------------------
# ШАГ 6: Create Dockerfile
# -----------------------------------------------------------------------------
echo ""
echo "🐳 ШАГ 6: Creating Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "bot.py"]
EOF
echo "  → Dockerfile created"

# -----------------------------------------------------------------------------
# ШАГ 7: Build Docker image and import to K3s
# -----------------------------------------------------------------------------
echo ""
echo "🔨 ШАГ 7: Building Docker image..."
docker build -t el-bot:latest .
echo "  → Docker image built"

echo ""
echo "📦 Importing to K3s containerd..."
docker save el-bot:latest | sudo k3s ctr images import -
echo "  → Image imported to K3s"

# -----------------------------------------------------------------------------
# ШАГ 8: Create K8s Secret
# -----------------------------------------------------------------------------
echo ""
echo "🔐 ШАГ 8: Creating K8s Secret..."
cat > k8s-secret.yaml << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: el-bot-secret
  namespace: bots
type: Opaque
stringData:
  TELEGRAM_BOT_TOKEN: "8354578179:AAGV7a7sCDqH5URcvRtTnJBrdqVWPGbBDEc"
  GITHUB_TOKEN: "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"
  TELEGRAM_ADMIN_ID: "290274837"
  GITHUB_REPO: "Mdyuzhev/errorlens"
EOF
kubectl apply -f k8s-secret.yaml
echo "  → Secret applied"

# Clean up secret file (security!)
rm -f k8s-secret.yaml
echo "  → Secret file removed (security)"

# -----------------------------------------------------------------------------
# ШАГ 9: Create K8s Deployment
# -----------------------------------------------------------------------------
echo ""
echo "🚀 ШАГ 9: Creating K8s Deployment..."
cat > k8s-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: el-bot
  namespace: bots
  labels:
    app: el-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: el-bot
  template:
    metadata:
      labels:
        app: el-bot
    spec:
      containers:
      - name: el-bot
        image: el-bot:latest
        imagePullPolicy: Never
        envFrom:
        - secretRef:
            name: el-bot-secret
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
      restartPolicy: Always
EOF
kubectl apply -f k8s-deployment.yaml
echo "  → Deployment applied"

# -----------------------------------------------------------------------------
# ШАГ 10: Check deployment status
# -----------------------------------------------------------------------------
echo ""
echo "⏳ ШАГ 10: Waiting for pod to start..."
sleep 5

echo ""
echo "📊 Pod status:"
kubectl get pods -n bots

echo ""
echo "📜 Pod logs (last 20 lines):"
kubectl logs -n bots -l app=el-bot --tail=20 2>/dev/null || echo "  → Pod not ready yet, check logs manually"

# -----------------------------------------------------------------------------
# Final status
# -----------------------------------------------------------------------------
echo ""
echo "================================"
echo "✅ EL_Bot Deployment Complete!"
echo "================================"
echo ""
echo "📁 Files created in: ~/projects/bots/el-bot/"
ls -la ~/projects/bots/el-bot/
echo ""
echo "🔍 To check status:"
echo "   kubectl get pods -n bots"
echo "   kubectl logs -n bots -l app=el-bot -f"
echo ""
echo "🔄 To restart:"
echo "   kubectl rollout restart deployment/el-bot -n bots"
echo ""
echo "🤖 Now test in Telegram: @ErrorLensBot"
echo ""
