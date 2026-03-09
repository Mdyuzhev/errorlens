#!/bin/bash
set -e

REPO_DIR="/opt/errorlens"
COMPOSE_DIR="$REPO_DIR/docker"

echo "[$(date)] Starting deploy..."

cd "$REPO_DIR"
git pull origin main

cd "$COMPOSE_DIR"
# Ensure Redis is running (dependency for backend, generator, collab)
docker compose up -d redis
docker compose build --no-cache backend nginx
docker compose up -d --no-deps backend generator collab nginx

echo "[$(date)] Deploy finished."
