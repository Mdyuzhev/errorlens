#!/usr/bin/env bash
# ErrorLens Deploy Script
# Usage:
#   ./scripts/deploy.sh           — full deploy (build + migrate + restart)
#   ./scripts/deploy.sh --no-build — only restart (skip npm + docker build)
#   ./scripts/deploy.sh --frontend-only — rebuild only nginx/frontend

set -euo pipefail

REPO_DIR="/opt/errorlens"
COMPOSE="docker compose -f $REPO_DIR/docker/docker-compose.yml"
LOG_FILE="$REPO_DIR/scripts/deploy.log"

NO_BUILD=false
FRONTEND_ONLY=false

for arg in "$@"; do
  case $arg in
    --no-build)      NO_BUILD=true ;;
    --frontend-only) FRONTEND_ONLY=true ;;
  esac
done

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "=== ErrorLens Deploy Start ==="
log "Mode: no_build=$NO_BUILD frontend_only=$FRONTEND_ONLY"

cd "$REPO_DIR"

# ── 1. Git pull ──────────────────────────────────────────────────────────────
log "[1/6] Git pull..."
git pull origin main 2>&1 | tail -5 | while read l; do log "  git: $l"; done

# ── 2. Alembic migrations ────────────────────────────────────────────────────
log "[2/6] Running Alembic migrations..."
$COMPOSE exec -T backend alembic upgrade head 2>&1 | while read l; do log "  alembic: $l"; done
log "  Migrations OK"

# ── 3. Build ─────────────────────────────────────────────────────────────────
if [ "$NO_BUILD" = false ]; then
  if [ "$FRONTEND_ONLY" = true ]; then
    log "[3/6] Rebuilding nginx (frontend only)..."
    $COMPOSE up --build --force-recreate --no-cache -d nginx
  else
    log "[3/6] Rebuilding backend + nginx..."
    $COMPOSE up --build --force-recreate -d backend nginx \
      generator notification-worker automation-worker launch-worker
  fi
else
  log "[3/6] Skipping build (--no-build)"
fi

# ── 4. Wait for healthy ───────────────────────────────────────────────────────
log "[4/6] Waiting for containers to be healthy..."
sleep 10
TIMEOUT=60
ELAPSED=0
until [ "$($COMPOSE ps | grep -c 'healthy')" -ge 3 ] || [ $ELAPSED -ge $TIMEOUT ]; do
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  log "  Waiting... ${ELAPSED}s"
done

# ── 5. Verify nginx bundle hash ───────────────────────────────────────────────
log "[5/6] Verifying nginx bundle..."
HOST_HASH=$(ls "$REPO_DIR/dashboard-vue/dist/assets/" | grep 'index-' | head -1)
CONTAINER_HASH=$(docker exec errorlens-nginx-1 \
  ls /usr/share/nginx/html/dashboard-vue/dist/assets/ | grep 'index-' | head -1 2>/dev/null || echo "none")

if [ "$HOST_HASH" = "$CONTAINER_HASH" ] && [ -n "$HOST_HASH" ]; then
  log "  ✅ Nginx bundle OK: $HOST_HASH"
else
  log "  ⚠️  Bundle mismatch: host=$HOST_HASH container=$CONTAINER_HASH"
  log "     Forcing nginx rebuild..."
  $COMPOSE up --build --force-recreate --no-cache -d nginx
  sleep 15
  CONTAINER_HASH=$(docker exec errorlens-nginx-1 \
    ls /usr/share/nginx/html/dashboard-vue/dist/assets/ | grep 'index-' | head -1)
  if [ "$HOST_HASH" = "$CONTAINER_HASH" ]; then
    log "  ✅ Nginx bundle fixed: $CONTAINER_HASH"
  else
    log "  ❌ CRITICAL: Nginx bundle still mismatched after rebuild!"
    exit 1
  fi
fi

# ── 6. Health checks ─────────────────────────────────────────────────────────
log "[6/6] Health checks..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health)
if [ "$API_STATUS" = "200" ]; then
  log "  ✅ API health: $API_STATUS"
else
  log "  ❌ API health: $API_STATUS"
  exit 1
fi

NGINX_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/nginx-health)
if [ "$NGINX_STATUS" = "200" ]; then
  log "  ✅ Nginx: $NGINX_STATUS"
else
  log "  ❌ Nginx: $NGINX_STATUS"
fi

log "=== Deploy Complete ==="
log "Dashboard: http://192.168.1.74:3000/dashboard/"
