#!/bin/bash
# =============================================================================
# EL_Bot v5 Deployment Script for K3s
# With Claude CLI + 3 parallel agents
# =============================================================================

set -e

echo "🤖 EL_Bot v5 Deployment Started!"
echo "================================"

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
NAMESPACE="bots"
BOT_NAME="el-bot"
IMAGE_NAME="el-bot:v5"
PROJECT_DIR="$HOME/projects/bots/el-bot"

# Secrets (update these!)
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-8354578179:AAGV7a7sCDqH5URcvRtTnJBrdqVWPGbBDEc}"
GITHUB_TOKEN="${GITHUB_TOKEN:-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}"
TELEGRAM_ADMIN_ID="${TELEGRAM_ADMIN_ID:-290274837}"
GITHUB_REPO="${GITHUB_REPO:-Mdyuzhev/errorlens}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-your_key_here}"

# -----------------------------------------------------------------------------
# Step 1: Create namespace
# -----------------------------------------------------------------------------
echo ""
echo "📦 Step 1: Creating namespace '$NAMESPACE'..."
kubectl create namespace $NAMESPACE 2>/dev/null || echo "  → Namespace already exists"

# -----------------------------------------------------------------------------
# Step 2: Create project directory
# -----------------------------------------------------------------------------
echo ""
echo "📁 Step 2: Creating project directory..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
echo "  → Working directory: $(pwd)"

# -----------------------------------------------------------------------------
# Step 3: Create requirements.txt
# -----------------------------------------------------------------------------
echo ""
echo "📋 Step 3: Creating requirements.txt..."
cat > requirements.txt << 'EOF'
python-telegram-bot==21.3
httpx==0.27.0
psutil==5.9.8
aiofiles==23.2.1
EOF
echo "  → requirements.txt created"

# -----------------------------------------------------------------------------
# Step 4: Create settings.local.json for Claude
# -----------------------------------------------------------------------------
echo ""
echo "⚙️ Step 4: Creating Claude settings..."
cat > settings.local.json << 'EOF'
{
  "permissions": {
    "allow": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch", "Task", "TodoWrite", "NotebookEdit"]
  },
  "preferences": {
    "language": "russian",
    "communication_style": "friendly_professional"
  },
  "memory": {
    "project": "ErrorLens - AI-powered QA platform",
    "stack": {
      "backend": "Python/FastAPI + PostgreSQL + Alembic + SQLAlchemy",
      "frontend": "Vue 3 + Vite dashboard",
      "bookmarklet": "Vanilla JS IIFE"
    }
  }
}
EOF
echo "  → settings.local.json created"

# -----------------------------------------------------------------------------
# Step 5: Create Dockerfile
# -----------------------------------------------------------------------------
echo ""
echo "🐳 Step 5: Creating Dockerfile..."
cat > Dockerfile << 'EOF'
# EL_Bot v5 + Claude Agent Runner
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Claude CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create working directories
WORKDIR /app
RUN mkdir -p /app/tasks /app/logs /app/projects/errorlens/.claude

# Copy settings for Claude
COPY settings.local.json /app/projects/errorlens/.claude/

# Copy bot files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot_v5.py .

# Environment variables
ENV TELEGRAM_BOT_TOKEN=""
ENV GITHUB_TOKEN=""
ENV TELEGRAM_ADMIN_ID=""
ENV GITHUB_REPO="Mdyuzhev/errorlens"
ENV ANTHROPIC_API_KEY=""
ENV AGENT_TASKS_DIR="/app/tasks"
ENV AGENT_MAX_CONCURRENT="3"
ENV PROJECT_DIR="/app/projects/errorlens"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python bot_v5.py" || exit 1

CMD ["python", "bot_v5.py"]
EOF
echo "  → Dockerfile created"

# -----------------------------------------------------------------------------
# Step 6: Create bot_v5.py (embedded)
# -----------------------------------------------------------------------------
echo ""
echo "🐍 Step 6: Creating bot_v5.py..."
# This would be the full bot_v5.py content - for brevity, copy from local
# In real deployment, copy the file from your local machine
cat > bot_v5.py << 'BOTEOF'
#!/usr/bin/env python3
"""
EL_Bot v5 - Telegram bot for GitHub Issues + Claude Agent Runner
See full source at: el-bot-files/bot_v5.py
"""
# PLACEHOLDER - Copy actual bot_v5.py content here
# Or use: scp local:el-bot-files/bot_v5.py server:$PROJECT_DIR/
print("Please copy bot_v5.py from source!")
BOTEOF
echo "  → bot_v5.py placeholder created"
echo "  ⚠️  Remember to copy actual bot_v5.py!"

# -----------------------------------------------------------------------------
# Step 7: Build Docker image
# -----------------------------------------------------------------------------
echo ""
echo "🔨 Step 7: Building Docker image..."
docker build -t $IMAGE_NAME .
echo "  → Docker image built"

echo ""
echo "📦 Importing to K3s containerd..."
docker save $IMAGE_NAME | sudo k3s ctr images import -
echo "  → Image imported to K3s"

# -----------------------------------------------------------------------------
# Step 8: Create K8s Secret
# -----------------------------------------------------------------------------
echo ""
echo "🔐 Step 8: Creating K8s Secret..."
cat > k8s-secret.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${BOT_NAME}-secret
  namespace: $NAMESPACE
type: Opaque
stringData:
  TELEGRAM_BOT_TOKEN: "$TELEGRAM_BOT_TOKEN"
  GITHUB_TOKEN: "$GITHUB_TOKEN"
  TELEGRAM_ADMIN_ID: "$TELEGRAM_ADMIN_ID"
  GITHUB_REPO: "$GITHUB_REPO"
  ANTHROPIC_API_KEY: "$ANTHROPIC_API_KEY"
EOF
kubectl apply -f k8s-secret.yaml
rm -f k8s-secret.yaml
echo "  → Secret applied and file removed"

# -----------------------------------------------------------------------------
# Step 9: Create PersistentVolumeClaim for tasks
# -----------------------------------------------------------------------------
echo ""
echo "💾 Step 9: Creating PersistentVolumeClaim..."
cat > k8s-pvc.yaml << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${BOT_NAME}-tasks
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${BOT_NAME}-project
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
EOF
kubectl apply -f k8s-pvc.yaml
echo "  → PVCs created"

# -----------------------------------------------------------------------------
# Step 10: Create K8s Deployment
# -----------------------------------------------------------------------------
echo ""
echo "🚀 Step 10: Creating K8s Deployment..."
cat > k8s-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $BOT_NAME
  namespace: $NAMESPACE
  labels:
    app: $BOT_NAME
spec:
  replicas: 1
  selector:
    matchLabels:
      app: $BOT_NAME
  template:
    metadata:
      labels:
        app: $BOT_NAME
    spec:
      containers:
      - name: $BOT_NAME
        image: $IMAGE_NAME
        imagePullPolicy: Never
        envFrom:
        - secretRef:
            name: ${BOT_NAME}-secret
        env:
        - name: AGENT_TASKS_DIR
          value: "/app/tasks"
        - name: AGENT_MAX_CONCURRENT
          value: "3"
        - name: PROJECT_DIR
          value: "/app/projects/errorlens"
        volumeMounts:
        - name: tasks
          mountPath: /app/tasks
        - name: project
          mountPath: /app/projects/errorlens
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      volumes:
      - name: tasks
        persistentVolumeClaim:
          claimName: ${BOT_NAME}-tasks
      - name: project
        persistentVolumeClaim:
          claimName: ${BOT_NAME}-project
      restartPolicy: Always
EOF
kubectl apply -f k8s-deployment.yaml
echo "  → Deployment applied"

# -----------------------------------------------------------------------------
# Step 11: Wait and check status
# -----------------------------------------------------------------------------
echo ""
echo "⏳ Step 11: Waiting for pod to start..."
sleep 10

echo ""
echo "📊 Pod status:"
kubectl get pods -n $NAMESPACE -l app=$BOT_NAME

echo ""
echo "📜 Pod logs:"
kubectl logs -n $NAMESPACE -l app=$BOT_NAME --tail=30 2>/dev/null || echo "  → Pod not ready yet"

# -----------------------------------------------------------------------------
# Final status
# -----------------------------------------------------------------------------
echo ""
echo "================================"
echo "✅ EL_Bot v5 Deployment Complete!"
echo "================================"
echo ""
echo "📁 Files: $PROJECT_DIR/"
ls -la "$PROJECT_DIR/"
echo ""
echo "🔍 Commands:"
echo "   kubectl get pods -n $NAMESPACE"
echo "   kubectl logs -n $NAMESPACE -l app=$BOT_NAME -f"
echo "   kubectl rollout restart deployment/$BOT_NAME -n $NAMESPACE"
echo ""
echo "🤖 Test in Telegram: @ErrorLensBot"
echo ""
echo "⚡ Features:"
echo "   • 3 parallel Claude agents"
echo "   • InlineKeyboard menu"
echo "   • /exec with task buttons"
echo "   • /lab server monitoring"
echo "   • Telegram notifications"
echo ""
