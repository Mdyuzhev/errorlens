#!/usr/bin/env bash
# populate_project.sh — Push autotest-demo files to GitLab via API
# Usage: ./populate_project.sh
#
# Reads GITLAB_URL, GITLAB_ROOT_TOKEN, GITLAB_PROJECT_ID from .env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env"

GITLAB_API="${GITLAB_URL}/api/v4"
AUTH_HEADER="PRIVATE-TOKEN: ${GITLAB_ROOT_TOKEN}"
PROJECT_API="${GITLAB_API}/projects/${GITLAB_PROJECT_ID}/repository/files"
AUTOTEST_DIR="${SCRIPT_DIR}/autotest-demo"

# URL-encode file path (replace / with %2F)
urlencode_path() {
    echo -n "$1" | sed 's|/|%2F|g'
}

# Create or update a file in GitLab repository
push_file() {
    local file_path="$1"
    local relative_path="${file_path#${AUTOTEST_DIR}/}"
    local encoded_path
    encoded_path=$(urlencode_path "$relative_path")
    local content
    content=$(base64 -w 0 < "$file_path" 2>/dev/null || base64 -i "$file_path")

    # Check if file exists
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "$AUTH_HEADER" \
        "${PROJECT_API}/${encoded_path}?ref=main")

    if [ "$http_code" = "200" ]; then
        # Update existing file
        curl -s -X PUT "${PROJECT_API}/${encoded_path}" \
            -H "$AUTH_HEADER" \
            -H "Content-Type: application/json" \
            -d "{\"branch\": \"main\", \"content\": \"${content}\", \"commit_message\": \"update: ${relative_path}\", \"encoding\": \"base64\"}" \
            > /dev/null
        echo "  updated: ${relative_path}"
    else
        # Create new file
        curl -s -X POST "${PROJECT_API}/${encoded_path}" \
            -H "$AUTH_HEADER" \
            -H "Content-Type: application/json" \
            -d "{\"branch\": \"main\", \"content\": \"${content}\", \"commit_message\": \"init: add ${relative_path}\", \"encoding\": \"base64\"}" \
            > /dev/null
        echo "  created: ${relative_path}"
    fi
}

echo "=== Pushing autotest-demo files to GitLab ==="
echo "GitLab: ${GITLAB_URL}"
echo "Project ID: ${GITLAB_PROJECT_ID}"
echo ""

# List of files to push (order matters for first commit)
FILES=(
    "README.md"
    "requirements.txt"
    "pytest.ini"
    "conftest.py"
    ".gitlab-ci.yml"
    "tests/__init__.py"
    "tests/auth/__init__.py"
    "tests/auth/test_login.py"
    "tests/api/__init__.py"
    "tests/api/test_users.py"
    "tests/api/test_products.py"
    "tests/ui/__init__.py"
    "tests/ui/test_search.py"
    "tests/integration/__init__.py"
    "tests/integration/test_checkout.py"
)

for file in "${FILES[@]}"; do
    full_path="${AUTOTEST_DIR}/${file}"
    if [ -f "$full_path" ]; then
        push_file "$full_path"
    else
        echo "  WARNING: ${file} not found, skipping"
    fi
done

echo ""
echo "=== Creating pipeline schedule ==="

# Create nightly schedule
SCHEDULE_RESPONSE=$(curl -s -X POST "${GITLAB_API}/projects/${GITLAB_PROJECT_ID}/pipeline_schedules" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d '{
        "description": "Nightly autotest run",
        "ref": "main",
        "cron": "0 2 * * *",
        "cron_timezone": "Europe/Moscow",
        "active": true
    }')

SCHEDULE_ID=$(echo "$SCHEDULE_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
if [ -n "$SCHEDULE_ID" ]; then
    echo "  Schedule created (id: ${SCHEDULE_ID}): daily at 02:00 MSK"
else
    echo "  Schedule may already exist or creation failed"
    echo "  Response: ${SCHEDULE_RESPONSE}"
fi

echo ""
echo "=== Done ==="
echo "Project: ${GITLAB_URL}/qa-team/autotest-demo"
echo "Pipelines: ${GITLAB_URL}/qa-team/autotest-demo/-/pipelines"
