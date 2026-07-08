#!/usr/bin/env python3
"""Query provider count trends from the database."""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / "provider_tracking" / "providers.db"

def show_daily_trend(country_code, days=7):
    """Show daily trend for a country (count at same time each day)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get latest hour from each day
    query = """
    SELECT 
        DATE(timestamp) as date,
        MAX(timestamp) as latest_time,
        provider_count
    FROM provider_counts
    WHERE country_code = ?
    GROUP BY DATE(timestamp)
    ORDER BY timestamp DESC
    LIMIT ?
    """
    
    cursor.execute(query, (country_code.lower(), days))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"No data found for country: {country_code}")
        return
    
    # Calculate daily changes
    rows.reverse()
    print(f"\n{rows[0][2] if rows else '?'} providers in {country_code.upper()} (latest)")
    print(f"{'Date':<12} {'Time':<9} {'Count':<8} {'Change':<8}")
    print("-" * 40)
    
    prev_count = None
    for date, time, count in rows:
        change = ""
        if prev_count is not None:
            delta = count - prev_count
            change = f"{delta:+d}" if delta != 0 else "—"
        print(f"{date:<12} {time.split()[1]:<9} {count:<8} {change:<8}")
        prev_count = count

def show_top_countries(days=1, metric="current"):
    """Show top 20 countries by provider count."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if metric == "current":
        query = """
        SELECT country_name, country_code, provider_count
        FROM provider_counts
        WHERE timestamp = (SELECT MAX(timestamp) FROM provider_counts)
        ORDER BY provider_count DESC
        LIMIT 20
        """
    elif metric == "growth":
        # Growth over last N days
        from datetime import datetime, timedelta
        target_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = """
        WITH latest AS (
            SELECT country_code, provider_count
            FROM provider_counts
            WHERE timestamp = (SELECT MAX(timestamp) FROM provider_counts)
        ),
        oldest AS (
            SELECT country_code, provider_count
            FROM provider_counts
            WHERE DATE(timestamp) = ?
            AND timestamp = (
                SELECT MIN(timestamp)
                FROM provider_counts p2
                WHERE DATE(p2.timestamp) = ?
                AND p2.country_code = provider_counts.country_code
            )
        )
        SELECT l.country_code, l.provider_count - COALESCE(o.provider_count, 0) as growth
        FROM latest l
        LEFT JOIN oldest o ON l.country_code = o.country_code
        ORDER BY growth DESC
        LIMIT 20
        """
        cursor.execute(query, (target_date, target_date))
    rows = cursor.fetchall()
    conn.close()
    
    if metric == "current":
        print(f"\nTop 20 countries by provider count:")
        print(f"{'Rank':<5} {'Country':<25} {'Code':<5} {'Providers':<12}")
        print("-" * 50)
        for i, (name, code, count) in enumerate(rows, 1):
            print(f"{i:<5} {name:<25} {code.upper():<5} {count:<12}")
    else:
        print(f"\nTop 20 countries by growth (last {days} days):")
        print(f"{'Rank':<5} {'Country Code':<15} {'Growth':<12}")
        print("-" * 35)
        for i, (code, growth) in enumerate(rows, 1):
            direction = "↑" if growth > 0 else "↓" if growth < 0 else "—"
            print(f"{i:<5} {code.upper():<15} {direction} {growth:+d}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  query_trends.py trend <country_code> [days]  # Show trend for a country")
        print("  query_trends.py top [current|growth] [days]   # Show top countries")
        print("\nExamples:")
        print("  query_trends.py trend us 7      # US trend last 7 days")
        print("  query_trends.py top current     # Top countries now")
        print("  query_trends.py top growth 1    # Top growth last day")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "trend":
        country = sys.argv[2] if len(sys.argv) > 2 else "us"
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        show_daily_trend(country, days)
    elif cmd == "top":
        metric = sys.argv[2] if len(sys.argv) > 2 else "current"
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        show_top_countries(days, metric)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
