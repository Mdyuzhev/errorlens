#!/bin/bash
set -e

REPO_DIR="/opt/errorlens"
COMPOSE_DIR="$REPO_DIR/docker"

echo "[$(date)] Starting deploy..."

cd "$REPO_DIR"
git fetch origin main
git reset --hard origin/main

cd "$COMPOSE_DIR"
# 1. Ensure stateful services are running
docker compose up -d redis

# 2. Rebuild and restart application services (not postgres/minio/redis)
docker compose up --build -d backend generator notification-worker collab

# 3. Apply database migrations
docker compose exec -T backend alembic upgrade head

# 4. Wait for backend to be healthy before restarting nginx
for i in $(seq 1 30); do
    if docker compose exec -T backend curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "[$(date)] Backend is healthy"
        break
    fi
    echo "Waiting for backend... ($i/30)"
    sleep 5
done

# 5. Force-recreate nginx so it re-resolves backend IP via Docker DNS
docker compose up --build --force-recreate -d nginx

echo "[$(date)] Deploy finished."
