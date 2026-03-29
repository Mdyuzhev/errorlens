#!/usr/bin/env bash
# Quick health check — вывести статус всех контейнеров

set -euo pipefail
COMPOSE="docker compose -f /opt/errorlens/docker/docker-compose.yml"

echo "=== ErrorLens Health Check $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""

# Container status
echo "Containers:"
$COMPOSE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
  docker ps --filter "name=errorlens" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "API Endpoints:"
for url in \
  "http://localhost:3000/api/health" \
  "http://localhost:3000/nginx-health" \
  "http://localhost:3000/dashboard/"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  icon="✅"
  [ "$status" != "200" ] && icon="❌"
  printf "  %s %-50s → %s\n" "$icon" "$url" "$status"
done

echo ""
echo "Nginx bundle:"
HOST=$(ls /opt/errorlens/dashboard-vue/dist/assets/ | grep 'index-' | head -1 2>/dev/null || echo "none")
CONT=$(docker exec errorlens-nginx-1 \
  ls /usr/share/nginx/html/dashboard-vue/dist/assets/ | grep 'index-' | head -1 2>/dev/null || echo "none")
if [ "$HOST" = "$CONT" ] && [ "$HOST" != "none" ]; then
  echo "  ✅ Match: $HOST"
else
  echo "  ❌ Mismatch: host=$HOST container=$CONT"
fi
