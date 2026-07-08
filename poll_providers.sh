#!/bin/bash
set -e

DB="/home/user/provider_tracking/providers.db"
JWT_FILE="/home/user/.urnetwork/jwt"
LOG="/home/user/provider_tracking/poll.log"
ENV_FILE="/home/user/provider_tracking/.env"
FAIL_FILE="/home/user/provider_tracking/.poll_fail_count"
WEBHOOK_URL=""

if [ -f "$ENV_FILE" ]; then
  WEBHOOK_URL=$(grep "^DISCORD_WEBHOOK_URL=" "$ENV_FILE" | cut -d= -f2-)
fi

log() { echo "$(date): $*" >> "$LOG"; }

send_discord() {
  [ -n "$WEBHOOK_URL" ] && curl -s -H "Content-Type: application/json" \
    -d "{\"content\":\"$1\"}" "$WEBHOOK_URL" >/dev/null 2>&1 || true
}

# Check for jq
if ! command -v jq &>/dev/null; then
  log "ERROR: jq not found, install with: apt install jq"
  exit 1
fi

# Create DB and ath_atl table if they don't exist
sqlite3 "$DB" "CREATE TABLE IF NOT EXISTS provider_counts (
  timestamp TEXT NOT NULL,
  country_code TEXT NOT NULL,
  country_name TEXT NOT NULL,
  provider_count INTEGER NOT NULL,
  PRIMARY KEY (timestamp, country_code)
);
CREATE INDEX IF NOT EXISTS idx_country_timestamp ON provider_counts(country_code, timestamp);
CREATE TABLE IF NOT EXISTS ath_atl (
  metric_type TEXT PRIMARY KEY,
  value INTEGER NOT NULL,
  timestamp TEXT NOT NULL
);"

JWT=$(cat "$JWT_FILE")
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S")

DATA=""
for attempt in 1 2 3; do
  DATA=$(curl -s --connect-timeout 10 -H "Authorization: Bearer $JWT" \
    "https://api.bringyour.com/network/provider-locations" 2>/dev/null) || true
  if [ -n "$DATA" ] && echo "$DATA" | jq -e '.locations' >/dev/null 2>&1; then
    break
  fi
  log "Poll attempt $attempt failed, retrying..."
  sleep $((attempt * 5))
  DATA=""
done

if [ -z "$DATA" ]; then
  log "ERROR: All poll attempts failed"
  # Track failure count
  COUNT=0
  [ -f "$FAIL_FILE" ] && COUNT=$(cat "$FAIL_FILE")
  COUNT=$((COUNT + 1))
  echo "$COUNT" > "$FAIL_FILE"
  if [ "$COUNT" -ge 3 ]; then
    send_discord "🔴 **Shell poller failed ${COUNT}x consecutively** — check poll.log"
  fi
  exit 1
fi

# Reset failure count
echo "0" > "$FAIL_FILE" 2>/dev/null || true

TOTAL=0
while IFS=$'\t' read -r ts cc cn count; do
  sqlite3 "$DB" "INSERT OR REPLACE INTO provider_counts VALUES ('$ts', '$cc', '$cn', $count);"
  TOTAL=$((TOTAL + count))
done < <(echo "$DATA" | jq -r ".locations[] | \"$TIMESTAMP\t\(.country_code)\t\(.name)\t\(.provider_count)\"")

CURRENT_TOTAL=$(echo "$DATA" | jq '[.locations[].provider_count] | add')
ATH_VALUE=$(sqlite3 "$DB" "SELECT value FROM ath_atl WHERE metric_type='ath';")
ATL_VALUE=$(sqlite3 "$DB" "SELECT value FROM ath_atl WHERE metric_type='atl';")

if [ -z "$ATH_VALUE" ] || [ "$CURRENT_TOTAL" -gt "$ATH_VALUE" ]; then
  sqlite3 "$DB" "INSERT OR REPLACE INTO ath_atl (metric_type, value, timestamp) VALUES ('ath', $CURRENT_TOTAL, '$TIMESTAMP');"
  log "ATH updated: $CURRENT_TOTAL"
fi
if [ -z "$ATL_VALUE" ] || [ "$CURRENT_TOTAL" -lt "$ATL_VALUE" ]; then
  sqlite3 "$DB" "INSERT OR REPLACE INTO ath_atl (metric_type, value, timestamp) VALUES ('atl', $CURRENT_TOTAL, '$TIMESTAMP');"
  log "ATL updated: $CURRENT_TOTAL"
fi

log "Poll completed, total: $CURRENT_TOTAL at $TIMESTAMP"
