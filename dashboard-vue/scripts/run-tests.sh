#!/bin/bash
set -e

BASE_URL="http://192.168.1.74:3000"
REPORTS_DIR="cypress/reports"
LOG_FILE="$REPORTS_DIR/run-$(date +%Y%m%d-%H%M%S).log"

echo "=== EL072 Test Run: $(date) ===" | tee "$LOG_FILE"
echo "Target: $BASE_URL" | tee -a "$LOG_FILE"

mkdir -p "$REPORTS_DIR"

# Запустить Issues тесты
echo ""
echo "[1/2] Running Issues tests..." | tee -a "$LOG_FILE"
npx cypress run \
  --spec "cypress/e2e/issues.cy.js" \
  --config "baseUrl=$BASE_URL" \
  --reporter mochawesome \
  --reporter-options "reportDir=$REPORTS_DIR,reportFilename=issues-results,overwrite=true,html=false,json=true" \
  2>&1 | tee -a "$LOG_FILE" || true

# Запустить Articles тесты
echo ""
echo "[2/2] Running Articles tests..." | tee -a "$LOG_FILE"
npx cypress run \
  --spec "cypress/e2e/articles.cy.js" \
  --config "baseUrl=$BASE_URL" \
  --reporter mochawesome \
  --reporter-options "reportDir=$REPORTS_DIR,reportFilename=articles-results,overwrite=true,html=false,json=true" \
  2>&1 | tee -a "$LOG_FILE" || true

# Собрать сводку
echo ""
echo "=== RESULTS SUMMARY ===" | tee -a "$LOG_FILE"

ISSUES_JSON="$REPORTS_DIR/issues-results.json"
ARTICLES_JSON="$REPORTS_DIR/articles-results.json"

if [ -f "$ISSUES_JSON" ]; then
  echo "Issues:" | tee -a "$LOG_FILE"
  node -e "
    const r = require('./$ISSUES_JSON');
    const s = r.stats;
    console.log('  Pass: ' + s.passes + ' | Fail: ' + s.failures + ' | Pending: ' + s.pending + ' | Total: ' + s.tests);
  " | tee -a "$LOG_FILE" || echo "  (parse error)" | tee -a "$LOG_FILE"
fi

if [ -f "$ARTICLES_JSON" ]; then
  echo "Articles:" | tee -a "$LOG_FILE"
  node -e "
    const r = require('./$ARTICLES_JSON');
    const s = r.stats;
    console.log('  Pass: ' + s.passes + ' | Fail: ' + s.failures + ' | Pending: ' + s.pending + ' | Total: ' + s.tests);
  " | tee -a "$LOG_FILE" || echo "  (parse error)" | tee -a "$LOG_FILE"
fi

echo ""
echo "Reports: $REPORTS_DIR"
echo "Log: $LOG_FILE"

# Запустить скрипт заведения багов
echo ""
echo "=== Filing bugs from failed tests... ==="
node scripts/report-to-bugs.js "$BASE_URL" "$ISSUES_JSON" "$ARTICLES_JSON"
