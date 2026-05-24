#!/usr/bin/env python3
"""Export provider count data as CSV."""
import sqlite3
import sys
import csv
from pathlib import Path

DB_PATH = Path.home() / "provider_tracking" / "providers.db"

def export_all(output_file=None):
    """Export all data as CSV."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT timestamp, country_code, country_name, provider_count FROM provider_counts ORDER BY timestamp, country_code")
    rows = cursor.fetchall()
    conn.close()
    
    output = open(output_file, 'w') if output_file else sys.stdout
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'country_code', 'country_name', 'provider_count'])
    writer.writerows(rows)
    
    if output_file:
        output.close()
        print(f"Exported {len(rows)} rows to {output_file}")

def export_country(country_code, output_file=None):
    """Export data for a single country."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT timestamp, country_code, country_name, provider_count FROM provider_counts WHERE country_code = ? ORDER BY timestamp",
        (country_code.lower(),)
    )
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"No data for country: {country_code}")
        return
    
    output = open(output_file, 'w') if output_file else sys.stdout
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'country_code', 'country_name', 'provider_count'])
    writer.writerows(rows)
    
    if output_file:
        output.close()
        print(f"Exported {len(rows)} rows for {country_code.upper()} to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  export_csv.py all [output.csv]           # Export all data")
        print("  export_csv.py <country_code> [output.csv] # Export single country")
        print("\nExamples:")
        print("  export_csv.py all data.csv       # Export to file")
        print("  export_csv.py us                 # Export US to stdout")
        print("  export_csv.py de trends/germany.csv")
        sys.exit(1)
    
    if sys.argv[1] == "all":
        output = sys.argv[2] if len(sys.argv) > 2 else None
        export_all(output)
    else:
        country = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else None
        export_country(country, output)
