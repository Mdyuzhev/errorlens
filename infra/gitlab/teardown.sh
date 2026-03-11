#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping GitLab containers..."
docker compose down

if [ "${1:-}" = "--purge" ]; then
  echo "Removing all GitLab data..."
  rm -rf ./data
  echo "Done. GitLab data removed."
else
  echo "Containers stopped. Data preserved in ./data/"
  echo "To remove data: ./teardown.sh --purge"
fi
