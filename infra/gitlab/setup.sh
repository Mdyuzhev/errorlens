#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GITLAB_URL="http://localhost:8080"
ENV_FILE=".env"

# Load .env if exists
if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE"
fi

# ── Step 1: Wait for GitLab to be ready ──────────────────────────────
echo "Waiting for GitLab to start..."
ATTEMPTS=0
until curl -sf "$GITLAB_URL/-/health" > /dev/null; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ $ATTEMPTS -ge 20 ]; then
    echo "ERROR: GitLab did not start in time (10 minutes)"
    exit 1
  fi
  echo "  attempt $ATTEMPTS/20, waiting 30s..."
  sleep 30
done
echo "GitLab is ready."

# ── Step 2: Create Personal Access Token via Rails runner ─────────────
echo "Creating API token..."
GITLAB_TOKEN=$(docker exec errorlens-gitlab gitlab-rails runner "
  user = User.find_by_username('root')
  token = user.personal_access_tokens.find_by(name: 'errorlens-api')
  if token.nil?
    token = user.personal_access_tokens.create!(
      name: 'errorlens-api',
      scopes: ['api', 'read_user', 'read_repository', 'write_repository'],
      expires_at: 1.year.from_now
    )
  end
  puts token.token
" 2>/dev/null | tail -1)

if [ -z "$GITLAB_TOKEN" ]; then
  echo "ERROR: Failed to create API token"
  exit 1
fi

sed -i "s|GITLAB_ROOT_TOKEN=.*|GITLAB_ROOT_TOKEN=$GITLAB_TOKEN|" "$ENV_FILE"
echo "API token created and saved to .env"

# ── Step 3: Create group qa-team ──────────────────────────────────────
echo "Creating group qa-team..."
GROUP_ID=$(curl -sf -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/groups?search=qa-team" | python3 -c "
import sys, json
groups = json.load(sys.stdin)
matches = [g for g in groups if g['path'] == 'qa-team']
print(matches[0]['id'] if matches else '')
")

if [ -z "$GROUP_ID" ]; then
  GROUP_ID=$(curl -sf -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "QA Team", "path": "qa-team", "visibility": "internal"}' \
    "$GITLAB_URL/api/v4/groups" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
  echo "Group qa-team created (id: $GROUP_ID)"
else
  echo "Group qa-team already exists (id: $GROUP_ID)"
fi

# ── Step 4: Create project autotest-demo ──────────────────────────────
echo "Creating project autotest-demo..."
PROJECT_ID=$(curl -sf -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/groups/$GROUP_ID/projects?search=autotest-demo" | python3 -c "
import sys, json
projects = json.load(sys.stdin)
matches = [p for p in projects if p['path'] == 'autotest-demo']
print(matches[0]['id'] if matches else '')
")

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(curl -sf -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"autotest-demo\", \"namespace_id\": $GROUP_ID, \"visibility\": \"internal\", \"initialize_with_readme\": true}" \
    "$GITLAB_URL/api/v4/projects" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
  echo "Project autotest-demo created (id: $PROJECT_ID)"
else
  echo "Project autotest-demo already exists (id: $PROJECT_ID)"
fi

sed -i "s|GITLAB_PROJECT_ID=.*|GITLAB_PROJECT_ID=$PROJECT_ID|" "$ENV_FILE"

# ── Step 5: Register runner ───────────────────────────────────────────
echo "Registering GitLab Runner..."
RUNNER_REG_TOKEN=$(curl -sf -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/groups/$GROUP_ID" | python3 -c "import sys, json; print(json.load(sys.stdin).get('runners_token', ''))")

if [ -z "$RUNNER_REG_TOKEN" ]; then
  echo "ERROR: Failed to get runner registration token"
  exit 1
fi

# Check if runner already registered
EXISTING_RUNNER=$(docker exec errorlens-gitlab-runner gitlab-runner list 2>&1 | grep -c "errorlens-test-runner" || true)
if [ "$EXISTING_RUNNER" -eq 0 ]; then
  docker exec errorlens-gitlab-runner gitlab-runner register \
    --non-interactive \
    --url "http://gitlab" \
    --registration-token "$RUNNER_REG_TOKEN" \
    --executor "docker" \
    --docker-image "python:3.11-slim" \
    --description "errorlens-test-runner" \
    --tag-list "docker" \
    --docker-network-mode "host" \
    --docker-extra-hosts "host.docker.internal:host-gateway"
  echo "Runner registered"
else
  echo "Runner already registered"
fi

sed -i "s|RUNNER_TOKEN=.*|RUNNER_TOKEN=$RUNNER_REG_TOKEN|" "$ENV_FILE"

# ── Step 6: Create CI/CD group variables ──────────────────────────────
echo "Setting CI/CD group variables..."

# Re-read .env for ERRORLENS_URL and ERRORLENS_TOKEN
source "$ENV_FILE"

for VAR_KEY in ERRORLENS_URL ERRORLENS_TOKEN; do
  VAR_VALUE="${!VAR_KEY:-}"
  MASKED="false"
  [ "$VAR_KEY" = "ERRORLENS_TOKEN" ] && MASKED="true"

  # Check if variable exists
  EXISTS=$(curl -sf -o /dev/null -w "%{http_code}" -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    "$GITLAB_URL/api/v4/groups/$GROUP_ID/variables/$VAR_KEY" || true)

  if [ "$EXISTS" = "200" ]; then
    curl -sf -X PUT -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"value\": \"$VAR_VALUE\", \"masked\": $MASKED}" \
      "$GITLAB_URL/api/v4/groups/$GROUP_ID/variables/$VAR_KEY" > /dev/null
    echo "  $VAR_KEY updated"
  else
    curl -sf -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"key\": \"$VAR_KEY\", \"value\": \"$VAR_VALUE\", \"masked\": $MASKED}" \
      "$GITLAB_URL/api/v4/groups/$GROUP_ID/variables" > /dev/null
    echo "  $VAR_KEY created"
  fi
done

# ── Step 7: Summary ──────────────────────────────────────────────────
echo ""
echo "==========================================="
echo "  GitLab CE Setup Complete"
echo "==========================================="
echo "  GitLab URL:    $GITLAB_URL"
echo "  Login:         root"
echo "  Password:      ErrorLens2024!"
echo "  API Token:     $GITLAB_TOKEN"
echo ""
echo "  Group:         qa-team (id: $GROUP_ID)"
echo "  Project:       autotest-demo (id: $PROJECT_ID)"
echo "  Runner:        registered (tag: docker)"
echo ""
echo "  Next steps:"
echo "  1. Open $GITLAB_URL and verify"
echo "  2. Set ERRORLENS_TOKEN in infra/gitlab/.env"
echo "  3. Run EL022 to populate autotest-demo project"
echo "==========================================="
