#!/bin/bash
set -e

REPO_DIR="/opt/errorlens"
COMPOSE_DIR="$REPO_DIR/docker"

echo "[$(date)] Starting deploy..."

cd "$REPO_DIR"
git pull origin main

cd "$COMPOSE_DIR"
docker compose up --build -d --no-deps backend nginx

echo "[$(date)] Deploy finished."
