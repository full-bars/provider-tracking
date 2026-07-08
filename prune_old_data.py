#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path.home() / "provider_tracking" / "providers.db"
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
cursor.execute("DELETE FROM provider_counts WHERE timestamp < ?", (cutoff,))
deleted = cursor.rowcount
conn.commit()
conn.close()
print(f"Pruned {deleted} rows older than {cutoff}")
