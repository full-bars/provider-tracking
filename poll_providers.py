#!/usr/bin/env python3
import sqlite3
import json
import requests
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / "provider_tracking" / "providers.db"
JWT_FILE = Path.home() / ".urnetwork" / "jwt"
LOG_FILE = Path.home() / "provider_tracking" / "poll.log"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS provider_counts (
            timestamp TEXT NOT NULL,
            country_code TEXT NOT NULL,
            country_name TEXT NOT NULL,
            provider_count INTEGER NOT NULL,
            PRIMARY KEY (timestamp, country_code)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_country_timestamp 
        ON provider_counts(country_code, timestamp)
    """)
    conn.commit()
    conn.close()

def poll_api():
    jwt = JWT_FILE.read_text().strip()
    headers = {"Authorization": f"Bearer {jwt}"}
    response = requests.get(
        "https://api.bringyour.com/network/provider-locations",
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def store_data(data):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for location in data.get("locations", []):
        cursor.execute(
            "INSERT OR REPLACE INTO provider_counts VALUES (?, ?, ?, ?)",
            (
                timestamp,
                location["country_code"],
                location["name"],
                location["provider_count"]
            )
        )
    conn.commit()
    conn.close()

def log_message(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} — {msg}\n")

if __name__ == "__main__":
    try:
        init_db()
        data = poll_api()
        store_data(data)
        log_message("Poll successful")
    except Exception as e:
        log_message(f"ERROR: {e}")
        exit(1)
