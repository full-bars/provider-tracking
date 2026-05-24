#!/bin/bash
set -e

DB="/home/user/provider_tracking/providers.db"
JWT_FILE="/home/user/.urnetwork/jwt"

# Create DB if it doesn't exist
if [ ! -f "$DB" ]; then
  sqlite3 "$DB" "CREATE TABLE provider_counts (
    timestamp TEXT NOT NULL,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    provider_count INTEGER NOT NULL,
    PRIMARY KEY (timestamp, country_code)
  );
  CREATE INDEX idx_country_timestamp ON provider_counts(country_code, timestamp);"
fi

# Read JWT and poll API
JWT=$(cat "$JWT_FILE")
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S")

curl -s -H "Authorization: Bearer $JWT" \
  https://api.bringyour.com/network/provider-locations | \
  jq -r ".locations[] | \"$TIMESTAMP\t\(.country_code)\t\(.name)\t\(.provider_count)\"" | \
  while IFS=$'\t' read ts cc cn count; do
    sqlite3 "$DB" "INSERT OR REPLACE INTO provider_counts VALUES ('$ts', '$cc', '$cn', $count);"
  done

echo "$(date): Poll completed at $TIMESTAMP" >> /home/user/provider_tracking/poll.log
