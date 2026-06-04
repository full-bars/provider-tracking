#!/usr/bin/env python3
from flask import Flask, jsonify, render_template_string, request
from datetime import datetime, timedelta
import sqlite3
import json
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path.home() / "provider_tracking" / "providers.db"

REGIONS = {
    'us': 'North America', 'ca': 'North America', 'mx': 'North America',
    'gb': 'Europe', 'de': 'Europe', 'fr': 'Europe', 'es': 'Europe', 'fi': 'Europe',
    'nl': 'Europe', 'se': 'Europe', 'no': 'Europe', 'dk': 'Europe', 'it': 'Europe',
    'pl': 'Europe', 'cz': 'Europe', 'at': 'Europe', 'ch': 'Europe', 'be': 'Europe',
    'ie': 'Europe', 'pt': 'Europe', 'ru': 'Europe', 'ua': 'Europe', 'ro': 'Europe',
    'bg': 'Europe', 'hu': 'Europe', 'lt': 'Europe', 'lv': 'Europe', 'sk': 'Europe',
    'hr': 'Europe', 'rs': 'Europe', 'md': 'Europe', 'by': 'Europe', 'is': 'Europe',
    'lu': 'Europe', 'mt': 'Europe', 'si': 'Europe', 'cy': 'Europe', 'gr': 'Europe',
    'mk': 'Europe', 'al': 'Europe', 'ba': 'Europe', 'am': 'Europe', 'ge': 'Europe',
    'kz': 'Europe', 'az': 'Europe', 'xk': 'Europe', 'ee': 'Europe', 'li': 'Europe',
    'mc': 'Europe', 'ad': 'Europe', 'tr': 'Europe',
    'vn': 'Asia-Pacific', 'sg': 'Asia-Pacific', 'hk': 'Asia-Pacific', 'kr': 'Asia-Pacific',
    'in': 'Asia-Pacific', 'jp': 'Asia-Pacific', 'th': 'Asia-Pacific', 'my': 'Asia-Pacific',
    'id': 'Asia-Pacific', 'ph': 'Asia-Pacific', 'cn': 'Asia-Pacific', 'tw': 'Asia-Pacific',
    'bd': 'Asia-Pacific', 'kh': 'Asia-Pacific', 'mn': 'Asia-Pacific', 'mm': 'Asia-Pacific',
    'la': 'Asia-Pacific', 'nz': 'Asia-Pacific', 'au': 'Asia-Pacific', 'lk': 'Asia-Pacific',
    'np': 'Asia-Pacific', 'uz': 'Asia-Pacific', 'tj': 'Asia-Pacific', 'kg': 'Asia-Pacific',
    'pk': 'Asia-Pacific', 'ir': 'Middle East',
    'ae': 'Middle East', 'sa': 'Middle East', 'il': 'Middle East', 'jo': 'Middle East',
    'qa': 'Middle East', 'kw': 'Middle East', 'iq': 'Middle East', 'sy': 'Middle East',
    'lb': 'Middle East', 'ps': 'Middle East', 'bh': 'Middle East', 'om': 'Middle East',
    'br': 'South America', 'ar': 'South America', 'co': 'South America', 'cl': 'South America',
    'pe': 'South America', 'uy': 'South America', 'py': 'South America', 'ec': 'South America',
    'bo': 'South America', 've': 'South America', 'cr': 'South America', 'pa': 'South America',
    'hn': 'South America', 'gt': 'South America', 'jm': 'South America', 'do': 'South America',
    'pr': 'South America', 'ky': 'South America', 'bs': 'South America', 'vi': 'South America',
    'bq': 'South America', 'tt': 'South America', 'gd': 'South America',
    'ng': 'Africa', 'ma': 'Africa', 'ke': 'Africa', 'za': 'Africa', 'sn': 'Africa',
    'tz': 'Africa', 'ug': 'Africa', 'mz': 'Africa', 'gh': 'Africa', 'cd': 'Africa',
    'et': 'Africa', 'ga': 'Africa', 'ci': 'Africa', 'tn': 'Africa', 'eg': 'Africa',
    'ly': 'Africa', 'dz': 'Africa', 'mu': 'Africa', 'bw': 'Africa',
}

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/summary')
def api_summary():
    conn = get_db()
    cursor = conn.cursor()

    # Current totals
    cursor.execute("SELECT MAX(timestamp) as latest FROM provider_counts")
    latest = cursor.fetchone()['latest']

    cursor.execute("""
        SELECT SUM(provider_count) as total FROM provider_counts
        WHERE timestamp = ?
    """, (latest,))
    current_total = cursor.fetchone()['total']

    # Hour-over-hour delta
    hour_ago = (datetime.fromisoformat(latest) - timedelta(hours=1)).isoformat(sep=' ')
    cursor.execute("""
        SELECT SUM(provider_count) as total FROM provider_counts
        WHERE timestamp = (SELECT timestamp FROM provider_counts WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1)
    """, (hour_ago,))
    row = cursor.fetchone()
    hour_ago_total = row['total'] if row and row['total'] is not None else current_total
    hour_delta = current_total - hour_ago_total

    # Day-over-day delta
    day_ago = (datetime.fromisoformat(latest) - timedelta(days=1)).isoformat(sep=' ')
    cursor.execute("""
        SELECT SUM(provider_count) as total FROM provider_counts
        WHERE timestamp = (SELECT timestamp FROM provider_counts WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1)
    """, (day_ago,))
    row = cursor.fetchone()
    day_ago_total = row['total'] if row and row['total'] is not None else current_total
    day_delta = current_total - day_ago_total

    # Week-over-week delta
    week_ago = (datetime.fromisoformat(latest) - timedelta(days=7)).isoformat(sep=' ')
    cursor.execute("""
        SELECT SUM(provider_count) as total FROM provider_counts
        WHERE timestamp = (SELECT timestamp FROM provider_counts WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1)
    """, (week_ago,))
    row = cursor.fetchone()
    week_ago_total = row['total'] if row and row['total'] is not None else current_total
    week_delta = current_total - week_ago_total

    # Time periods for ranges
    week_ago = (datetime.fromisoformat(latest) - timedelta(days=7)).isoformat(sep=' ')
    two_week_ago = (datetime.fromisoformat(latest) - timedelta(days=14)).isoformat(sep=' ')
    month_ago = (datetime.fromisoformat(latest) - timedelta(days=30)).isoformat(sep=' ')

    # Top 10
    cursor.execute("""
        SELECT country_name, country_code, provider_count
        FROM provider_counts WHERE timestamp = ?
        ORDER BY provider_count DESC LIMIT 10
    """, (latest,))
    top_10 = [dict(row) for row in cursor.fetchall()]

    # High/low ranges
    cursor.execute("""
        WITH totals AS (
            SELECT SUM(provider_count) as total
            FROM provider_counts
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY timestamp
        )
        SELECT MAX(total) as high, MIN(total) as low FROM totals
    """, (hour_ago, latest))
    hour_range = cursor.fetchone()
    hour_high = hour_range['high'] or 0
    hour_low = hour_range['low'] or 0

    cursor.execute("""
        WITH totals AS (
            SELECT SUM(provider_count) as total
            FROM provider_counts
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY timestamp
        )
        SELECT MAX(total) as high, MIN(total) as low FROM totals
    """, (day_ago, latest))
    day_range = cursor.fetchone()
    day_high = day_range['high'] or 0
    day_low = day_range['low'] or 0

    cursor.execute("""
        WITH totals AS (
            SELECT SUM(provider_count) as total
            FROM provider_counts
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY timestamp
        )
        SELECT MAX(total) as high, MIN(total) as low FROM totals
    """, (week_ago, latest))
    week_range = cursor.fetchone()
    week_high = week_range['high'] or 0
    week_low = week_range['low'] or 0

    cursor.execute("""
        WITH totals AS (
            SELECT SUM(provider_count) as total
            FROM provider_counts
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY timestamp
        )
        SELECT MAX(total) as high, MIN(total) as low FROM totals
    """, (two_week_ago, latest))
    two_week_range = cursor.fetchone()
    two_week_high = two_week_range['high'] or 0
    two_week_low = two_week_range['low'] or 0

    cursor.execute("""
        WITH totals AS (
            SELECT SUM(provider_count) as total
            FROM provider_counts
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY timestamp
        )
        SELECT MAX(total) as high, MIN(total) as low FROM totals
    """, (month_ago, latest))
    month_range = cursor.fetchone()
    month_high = month_range['high'] or 0
    month_low = month_range['low'] or 0

    # All-time high
    cursor.execute("""
        WITH totals AS (
            SELECT timestamp, SUM(provider_count) as total
            FROM provider_counts GROUP BY timestamp
        )
        SELECT timestamp, total FROM totals ORDER BY total DESC LIMIT 1
    """)
    ath_row = cursor.fetchone()
    ath_value = ath_row['total'] if ath_row else current_total
    ath_timestamp = ath_row['timestamp'] if ath_row else latest

    # All-time low
    cursor.execute("""
        WITH totals AS (
            SELECT timestamp, SUM(provider_count) as total
            FROM provider_counts GROUP BY timestamp
        )
        SELECT timestamp, total FROM totals ORDER BY total ASC LIMIT 1
    """)
    atl_row = cursor.fetchone()
    atl_value = atl_row['total'] if atl_row else current_total
    atl_timestamp = atl_row['timestamp'] if atl_row else latest

    conn.close()
    return jsonify({
        'timestamp': latest,
        'total': current_total,
        'hour_delta': hour_delta,
        'day_delta': day_delta,
        'week_delta': week_delta,
        'top_10': top_10,
        'hour_range': [hour_low, hour_high],
        'day_range': [day_low, day_high],
        'week_range': [week_low, week_high],
        'two_week_range': [two_week_low, two_week_high],
        'month_range': [month_low, month_high],
        'ath': {'value': ath_value, 'timestamp': ath_timestamp},
        'atl': {'value': atl_value, 'timestamp': atl_timestamp},
    })

@app.route('/api/network_total')
def api_network_total():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, SUM(provider_count) as total
        FROM provider_counts
        GROUP BY timestamp
        ORDER BY timestamp DESC LIMIT 720
    """)
    data = [{'timestamp': row[0], 'total': row[1]} for row in cursor.fetchall()]
    data.reverse()

    # Add 24-hour moving average
    window = 24
    for i, row in enumerate(data):
        start = max(0, i - window + 1)
        row['ma'] = round(sum(d['total'] for d in data[start:i+1]) / (i - start + 1))

    conn.close()
    return jsonify(data)

@app.route('/api/live_total')
def api_live_total():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, SUM(provider_count) FROM provider_counts GROUP BY timestamp ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return jsonify({'timestamp': row[0], 'total': row[1]})

@app.route('/api/movers')
def api_movers():
    conn = get_db()
    cursor = conn.cursor()
    
    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]
    hour_ago = (datetime.fromisoformat(latest) - timedelta(hours=1)).isoformat(sep=' ')
    day_ago = (datetime.fromisoformat(latest) - timedelta(days=1)).isoformat(sep=' ')
    week_ago = (datetime.fromisoformat(latest) - timedelta(days=7)).isoformat(sep=' ')
    
    movers = {}
    for window, since in [('1h', hour_ago), ('24h', day_ago), ('7d', week_ago)]:
        cursor.execute(f"""
            WITH current AS (
                SELECT country_code, country_name, provider_count 
                FROM provider_counts WHERE timestamp = ?
            ),
            past AS (
                SELECT country_code, provider_count 
                FROM provider_counts 
                WHERE timestamp = (
                    SELECT MIN(timestamp) FROM provider_counts WHERE timestamp >= ?
                )
            )
            SELECT c.country_name, c.country_code, c.provider_count,
                   c.provider_count - COALESCE(p.provider_count, 0) as delta
            FROM current c
            LEFT JOIN past p ON c.country_code = p.country_code
            ORDER BY delta DESC
        """, (latest, since))
        gainers = [dict(row) for row in cursor.fetchmany(10)]
        
        cursor.execute(f"""
            WITH current AS (
                SELECT country_code, country_name, provider_count 
                FROM provider_counts WHERE timestamp = ?
            ),
            past AS (
                SELECT country_code, provider_count 
                FROM provider_counts 
                WHERE timestamp = (
                    SELECT MIN(timestamp) FROM provider_counts WHERE timestamp >= ?
                )
            )
            SELECT c.country_name, c.country_code, c.provider_count,
                   c.provider_count - COALESCE(p.provider_count, 0) as delta
            FROM current c
            LEFT JOIN past p ON c.country_code = p.country_code
            ORDER BY delta ASC
        """, (latest, since))
        losers = [dict(row) for row in cursor.fetchmany(10)]
        
        movers[window] = {'gainers': gainers, 'losers': losers}
    
    conn.close()
    return jsonify(movers)

@app.route('/api/anomalies')
def api_anomalies():
    conn = get_db()
    cursor = conn.cursor()

    threshold_pct = float(request.args.get('threshold', 15))
    threshold = threshold_pct / 100

    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]
    hour_ago = (datetime.fromisoformat(latest) - timedelta(hours=1)).isoformat(sep=' ')

    # Get current data
    cursor.execute("""
        SELECT country_code, country_name, provider_count
        FROM provider_counts WHERE timestamp = ?
        ORDER BY provider_count DESC
    """, (latest,))
    current_rows = [dict(row) for row in cursor.fetchall()]

    all_anomalies = []
    for current in current_rows:
        # Get each country's historical data (most recent at or before hour_ago)
        cursor.execute("""
            SELECT provider_count FROM provider_counts
            WHERE country_code = ? AND timestamp <= ?
            ORDER BY timestamp DESC LIMIT 1
        """, (current['country_code'], hour_ago))
        past_row = cursor.fetchone()

        if past_row and past_row[0] > 0:
            past_count = past_row[0]
            delta = current['provider_count'] - past_count
            pct_change = (delta / past_count) * 100

            if abs(pct_change) > threshold_pct:
                all_anomalies.append({
                    'country_code': current['country_code'],
                    'country_name': current['country_name'],
                    'provider_count': current['provider_count'],
                    'delta': delta,
                    'pct_change': pct_change
                })

    conn.close()

    gains = [a for a in all_anomalies if a['pct_change'] > 0]
    losses = [a for a in all_anomalies if a['pct_change'] < 0]

    gains.sort(key=lambda x: abs(x['pct_change']), reverse=True)
    losses.sort(key=lambda x: abs(x['pct_change']), reverse=True)

    anomalies = gains + losses
    return jsonify({'anomalies': anomalies, 'threshold': threshold_pct})

@app.route('/api/growth-projection')
def api_growth_projection():
    conn = get_db()
    cursor = conn.cursor()

    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]
    day_ago = (datetime.fromisoformat(latest) - timedelta(days=1)).isoformat(sep=' ')

    cursor.execute("SELECT SUM(provider_count) as total FROM provider_counts WHERE timestamp = ?", (latest,))
    current = cursor.fetchone()['total']

    cursor.execute("""
        SELECT SUM(provider_count) as total FROM provider_counts
        WHERE timestamp = (SELECT timestamp FROM provider_counts WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1)
    """, (day_ago,))
    row = cursor.fetchone()
    past = (row['total'] if row and row['total'] is not None else None) or current

    daily_growth = current - past
    growth_rate = (daily_growth / past * 100) if past > 0 else 0

    # Cap projections at reasonable bounds to avoid astronomical numbers from data anomalies
    capped_growth = max(-1000, min(1000, daily_growth))
    projected_30d = int(current + (capped_growth * 30))
    projected_90d = int(current + (capped_growth * 90))

    conn.close()
    return jsonify({
        'current': current,
        'daily_growth': daily_growth,
        'growth_rate': max(-100, min(100, growth_rate)),
        'projected_30d': max(0, projected_30d),
        'projected_90d': max(0, projected_90d)
    })

@app.route('/api/churn/<code>')
def api_churn(code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, provider_count
        FROM provider_counts
        WHERE country_code = ?
        ORDER BY timestamp DESC LIMIT 24
    """, (code.lower(),))

    data = [{'timestamp': row[0], 'count': row[1]} for row in cursor.fetchall()]
    data.reverse()

    if len(data) < 2:
        conn.close()
        return jsonify({'churn_rate': 0, 'volatility': 'N/A', 'data': data})

    changes = [abs(data[i+1]['count'] - data[i]['count']) for i in range(len(data)-1)]
    avg_change = sum(changes) / len(changes) if changes else 0
    volatility = 'high' if avg_change > 100 else 'medium' if avg_change > 50 else 'low'

    conn.close()
    return jsonify({'churn_rate': avg_change, 'volatility': volatility, 'data': data})

@app.route('/api/country-stats/<code>')
def api_country_stats(code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, provider_count
        FROM provider_counts
        WHERE country_code = ?
        ORDER BY timestamp DESC LIMIT 24
    """, (code.lower(),))

    data = [{'timestamp': row[0], 'count': row[1]} for row in cursor.fetchall()]
    data.reverse()

    if len(data) < 2:
        conn.close()
        return jsonify({'volatility': 'N/A', 'churn_rate': 0})

    changes = [abs(data[i+1]['count'] - data[i]['count']) for i in range(len(data)-1)]
    avg_change = sum(changes) / len(changes) if changes else 0
    volatility = 'high' if avg_change > 100 else 'medium' if avg_change > 50 else 'low'

    conn.close()
    return jsonify({'volatility': volatility, 'churn_rate': round(avg_change, 1)})

@app.route('/api/regions')
def api_regions():
    conn = get_db()
    cursor = conn.cursor()

    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]
    day_ago = (datetime.fromisoformat(latest) - timedelta(days=1)).isoformat(sep=' ')

    # Get current totals by region
    cursor.execute("""
        SELECT country_code, provider_count
        FROM provider_counts WHERE timestamp = ?
    """, (latest,))
    current_by_country = {row[0]: row[1] for row in cursor.fetchall()}

    # Get 24h-ago totals by region
    cursor.execute("""
        SELECT country_code, provider_count
        FROM provider_counts
        WHERE timestamp = (
            SELECT MAX(timestamp) FROM provider_counts WHERE timestamp <= ?
        )
    """, (day_ago,))
    past_by_country = {row[0]: row[1] for row in cursor.fetchall()}

    # Aggregate by region
    regions_data = {}
    for cc, current_count in current_by_country.items():
        region = REGIONS.get(cc, 'Other')
        if region not in regions_data:
            regions_data[region] = {'total': 0, 'past_total': 0}
        regions_data[region]['total'] += current_count
        regions_data[region]['past_total'] += past_by_country.get(cc, current_count)

    # Build response
    result = []
    for region, data in regions_data.items():
        delta = data['total'] - data['past_total']
        result.append({
            'region': region,
            'total': data['total'],
            'delta_24h': delta
        })

    result.sort(key=lambda x: x['total'], reverse=True)
    conn.close()
    return jsonify(result)

@app.route('/api/at-risk')
def api_at_risk():
    conn = get_db()
    cursor = conn.cursor()

    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]
    day_ago = (datetime.fromisoformat(latest) - timedelta(days=1)).isoformat(sep=' ')

    # Countries that are at 0 now but were non-zero 24h ago
    cursor.execute("""
        SELECT c.country_code, c.country_name,
               p.provider_count as prev_count, p.timestamp as last_seen_ts
        FROM (
            SELECT DISTINCT country_code, country_name FROM provider_counts WHERE timestamp = ? AND provider_count = 0
        ) c
        LEFT JOIN (
            SELECT country_code, provider_count, timestamp FROM provider_counts
            WHERE timestamp <= ? AND provider_count > 0
            ORDER BY country_code, timestamp DESC
        ) p ON c.country_code = p.country_code
        WHERE p.provider_count > 0
    """, (latest, day_ago))
    disappeared = [dict(row) for row in cursor.fetchall()]

    # Countries with 1-5 providers and declining in last 24h
    cursor.execute("""
        WITH current AS (
            SELECT country_code, country_name, provider_count
            FROM provider_counts WHERE timestamp = ? AND provider_count BETWEEN 1 AND 5
        ),
        past AS (
            SELECT country_code, provider_count
            FROM provider_counts
            WHERE timestamp = (
                SELECT MAX(timestamp) FROM provider_counts WHERE timestamp <= ?
            )
        )
        SELECT c.country_name, c.country_code, c.provider_count,
               COALESCE(c.provider_count - p.provider_count, 0) as delta_24h
        FROM current c
        LEFT JOIN past p ON c.country_code = p.country_code
        WHERE (p.provider_count IS NULL OR c.provider_count - p.provider_count < 0)
        ORDER BY c.provider_count ASC
    """, (latest, day_ago))
    near_zero = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return jsonify({
        'disappeared': disappeared,
        'near_zero': near_zero
    })

@app.route('/api/comparison/<code1>/<code2>')
def api_comparison(code1, code2):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, provider_count
        FROM provider_counts
        WHERE country_code = ?
        ORDER BY timestamp
    """, (code1.lower(),))
    data1 = [{'timestamp': row[0], 'code': code1.upper(), 'count': row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT timestamp, provider_count
        FROM provider_counts
        WHERE country_code = ?
        ORDER BY timestamp
    """, (code2.lower(),))
    data2 = [{'timestamp': row[0], 'code': code2.upper(), 'count': row[1]} for row in cursor.fetchall()]

    conn.close()
    return jsonify({'data1': data1, 'data2': data2})

@app.route('/api/movers-detailed')
def api_movers_detailed():
    conn = get_db()
    cursor = conn.cursor()

    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]

    # Define time windows in minutes
    windows = {
        '15m': 15,
        '1h': 60,
        '2h': 120,
        '3h': 180,
        '6h': 360,
        '12h': 720,
        '24h': 1440,
        '2d': 2880,
        '3d': 4320,
        '4d': 5760,
        '5d': 7200,
        '6d': 8640,
        '7d': 10080,
        '14d': 20160,
        '30d': 43200
    }

    latest_dt = datetime.fromisoformat(latest)

    # Get all countries in current snapshot
    cursor.execute("SELECT DISTINCT country_code FROM provider_counts WHERE timestamp = ? ORDER BY country_code", (latest,))
    all_countries = [row[0] for row in cursor.fetchall()]

    # Build deltas for each country and time window
    country_data = {}
    for cc in all_countries:
        country_data[cc] = {'code': cc, 'deltas': {}}

    # Get current counts
    cursor.execute("SELECT country_code, country_name, provider_count FROM provider_counts WHERE timestamp = ?", (latest,))
    for row in cursor.fetchall():
        cc = row[0]
        if cc in country_data:
            country_data[cc]['name'] = row[1]
            country_data[cc]['current'] = row[2]

    # Calculate deltas for each time window
    for window_name, minutes in windows.items():
        window_time = latest_dt - timedelta(minutes=minutes)
        window_str = window_time.isoformat(sep=' ')

        cursor.execute("""
            SELECT country_code, provider_count
            FROM provider_counts
            WHERE timestamp = (
                SELECT MAX(timestamp) FROM provider_counts
                WHERE timestamp <= ? AND country_code = provider_counts.country_code
            )
        """, (window_str,))

        past_counts = {row[0]: row[1] for row in cursor.fetchall()}

        for cc in country_data:
            past_count = past_counts.get(cc, country_data[cc].get('current', 0))
            delta = country_data[cc].get('current', 0) - past_count
            country_data[cc]['deltas'][window_name] = delta

    # Sort by 24h delta and get top 50
    sorted_countries = sorted(
        [data for data in country_data.values() if 'current' in data],
        key=lambda x: x['deltas'].get('24h', 0),
        reverse=True
    )

    gainers = sorted_countries[:50]
    losers = sorted(sorted_countries, key=lambda x: x['deltas'].get('24h', 0))[:50]

    conn.close()
    return jsonify({'gainers': gainers, 'losers': losers})

@app.route('/api/country/<code>')
def api_country(code):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, provider_count 
        FROM provider_counts 
        WHERE country_code = ? 
        ORDER BY timestamp DESC LIMIT 720
    """, (code.lower(),))
    data = [{'timestamp': row[0], 'count': row[1]} for row in cursor.fetchall()]
    data.reverse()
    
    conn.close()
    return jsonify(data)

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Provider Tracking Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f1419; color: #e0e6ed; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { font-size: 28px; margin-bottom: 30px; }
        .header { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #1a1f26; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; }
        .stat-value { font-size: 32px; font-weight: bold; color: #4ade80; }
        .stat-label { font-size: 12px; text-transform: uppercase; color: #9ca3af; margin-top: 5px; }
        .stat-delta { font-size: 14px; margin-top: 8px; color: #60a5fa; }
        .delta-positive { color: #4ade80; }
        .delta-negative { color: #f87171; }
        .inline-delta { font-size: 13px; margin-top: 4px; color: #e0e6ed; }
        .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .chart-card { background: #1a1f26; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; }
        .chart-card h3 { margin-bottom: 15px; color: #a0aec0; font-size: 14px; text-transform: uppercase; }
        .chart-container { position: relative; height: 300px; }
        .table-card { background: #1a1f26; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .table-card h3 { margin-bottom: 15px; color: #a0aec0; font-size: 14px; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 10px; border-bottom: 1px solid #2d3748; color: #a0aec0; font-size: 12px; }
        td { padding: 10px; border-bottom: 1px solid #2d3748; }
        .search-box { background: #1a1f26; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        input { background: #0f1419; border: 1px solid #2d3748; color: #e0e6ed; padding: 10px; border-radius: 4px; }
        .spinner { display: inline-block; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .last-update { color: #9ca3af; font-size: 12px; margin-top: 10px; }
        .alert-banner { background: #7f1d1d; border: 1px solid #991b1b; color: #fecaca; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: none; width: fit-content; }
        .alert-banner.show { display: block; }
        .alert-banner strong { color: #fee2e2; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
        .toggle-btn { background: #2d3748; border: 1px solid #4a5568; color: #e0e6ed; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 12px; }
        .toggle-btn.active { background: #4ade80; color: #0f1419; }
        .comparison-container { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
        .comparison-input { background: #1a1f26; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; }
        .comparison-input input { width: 100%; }
        .indicator { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
        .indicator.stable { background: #4ade80; }
        .indicator.warning { background: #facc15; }
        .indicator.unstable { background: #f87171; }
        .volatility { font-size: 10px; color: #9ca3af; font-style: italic; }
        .ticker-wrap { width: 100%; overflow: hidden; background: #0f1419; border-bottom: 1px solid #2d3748; padding: 10px 0; margin-bottom: 20px; white-space: nowrap; box-sizing: content-box; }
        .ticker-move { display: inline-block; padding-left: 100%; animation: ticker 120s linear infinite; }
        @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
        .ticker-item { display: inline-block; padding: 0 2rem; font-size: 14px; font-weight: bold; }
        .ticker-item.gain { color: #4ade80; }
        .ticker-item.loss { color: #f87171; }
        .hero-chart-card { background: #1a1f26; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .hero-chart-card h3 { margin-bottom: 15px; color: #a0aec0; font-size: 14px; text-transform: uppercase; display: flex; justify-content: space-between; }
        .live-badge { color: #4ade80; animation: blink 2s infinite; font-weight: bold; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .weekly-charts { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
        .weekly-charts .chart-card { background: #1a1f26; border: 1px solid #2d3748; border-radius: 8px; padding: 15px; }
        .weekly-charts .chart-container { height: 120px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Provider Network Dashboard</h1>

        <div class="ticker-wrap">
            <div class="ticker-move" id="ticker-content">
                <span style="color: #9ca3af; font-size: 14px;">Loading Live Ticker...</span>
            </div>
        </div>

        <div class="alert-banner" id="anomaly-alert">
            <strong>⚠️ Anomalies:</strong> <span id="anomaly-text" style="margin-left: 8px;"></span>
        </div>

        <div class="hero-chart-card">
            <h3><span>Live Network Activity</span> <span class="live-badge">🔴 LIVE</span></h3>
            <div class="chart-container" style="height: 200px;"><canvas id="liveChart"></canvas></div>
        </div>

        <div class="hero-chart-card">
            <h3><span>Network Total Over Time (Hourly)</span></h3>
            <div class="chart-container" style="height: 350px;"><canvas id="totalChart"></canvas></div>
        </div>

        <h3 style="color: #a0aec0; font-size: 14px; text-transform: uppercase; margin-bottom: 15px;">Monthly Breakdown (Week by Week)</h3>
        <div class="weekly-charts">
            <div class="chart-card">
                <h3 style="font-size: 12px;">Week 1 (Last 7 Days)</h3>
                <div class="chart-container"><canvas id="week1Chart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3 style="font-size: 12px;">Week 2</h3>
                <div class="chart-container"><canvas id="week2Chart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3 style="font-size: 12px;">Week 3</h3>
                <div class="chart-container"><canvas id="week3Chart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3 style="font-size: 12px;">Week 4</h3>
                <div class="chart-container"><canvas id="week4Chart"></canvas></div>
            </div>
        </div>

        <div class="header" id="header">
            <div class="stat-card">
                <div class="stat-value" id="total">-</div>
                <div class="stat-label">Total Network Providers</div>
                <div class="stat-delta"><span id="day-delta">-</span> (24h)</div>
                <div style="margin-top:10px; padding-top:10px; border-top:1px solid #2d3748;">
                    <div style="font-size:11px; color:#f59e0b;">▲ ATH &nbsp;<span id="ath-value" style="font-weight:600;">-</span> <span id="ath-date" style="color:#6b7280; font-size:10px;"></span></div>
                    <div style="font-size:11px; color:#f87171; margin-top:3px;">▼ ATL &nbsp;<span id="atl-value" style="font-weight:600;">-</span> <span id="atl-date" style="color:#6b7280; font-size:10px;"></span></div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="top-country">-</div>
                <div class="stat-label">Largest Country</div>
                <div class="stat-delta" id="top-country-code">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="hour-delta">-</div>
                <div class="stat-label">Change (1h)</div>
                <div style="margin-top: 8px;">
                    <div class="inline-delta">24h: <span id="day-delta-inline">-</span></div>
                    <div class="inline-delta">7d: <span id="week-delta-inline">-</span></div>
                </div>
                <div class="last-update">Refreshing in <span id="refresh-timer">5m</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="growth-rate">-</div>
                <div class="stat-label">Daily Growth Rate</div>
                <div class="stat-delta">→ <span id="projected-30d">-</span> in 30d</div>
            </div>
        </div>

        <div class="charts">
            <div class="chart-card">
                <h3>Top 10 Countries</h3>
                <div class="chart-container" style="height: 300px;"><canvas id="top25Chart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3>Provider Distribution</h3>
                <div class="chart-container" style="height: 300px;"><canvas id="distChart"></canvas></div>
            </div>
        </div>

        <div class="charts">
            <div class="chart-card">
                <h3>Regional Totals</h3>
                <div class="chart-container"><canvas id="regionChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3>Top Movers (24h)</h3>
                <div class="chart-container"><canvas id="moversChart"></canvas></div>
            </div>
        </div>
        
        <div class="table-card">
            <h3>Top 50 Gainers (24h)</h3>
            <table id="gainers-table" style="font-size: 12px;">
                <thead><tr><th>Country</th><th>Current</th><th>15m Δ</th><th>1h Δ</th><th>2h Δ</th><th>3h Δ</th><th>6h Δ</th><th>12h Δ</th><th style="background:rgba(74,222,128,0.15);border-bottom:2px solid #4ade80;">24h Δ ▼</th><th>2d Δ</th><th>3d Δ</th><th>4d Δ</th><th>5d Δ</th><th>6d Δ</th><th>7d Δ</th><th>14d Δ</th><th>30d Δ</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>

        <div class="table-card">
            <h3>Top 50 Losers (24h)</h3>
            <table id="losers-table" style="font-size: 12px;">
                <thead><tr><th>Country</th><th>Current</th><th>15m Δ</th><th>1h Δ</th><th>2h Δ</th><th>3h Δ</th><th>6h Δ</th><th>12h Δ</th><th style="background:rgba(74,222,128,0.15);border-bottom:2px solid #4ade80;">24h Δ ▼</th><th>2d Δ</th><th>3d Δ</th><th>4d Δ</th><th>5d Δ</th><th>6d Δ</th><th>7d Δ</th><th>14d Δ</th><th>30d Δ</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>

        <div class="table-card">
            <h3>⚠️ At Risk</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 12px;">
                <div>
                    <h4 style="color: #9ca3af; margin-bottom: 10px; font-size: 11px; text-transform: uppercase;">Disappeared (0 providers)</h4>
                    <div id="disappeared-list"></div>
                </div>
                <div>
                    <h4 style="color: #9ca3af; margin-bottom: 10px; font-size: 11px; text-transform: uppercase;">Near Zero (1-5, declining)</h4>
                    <div id="near-zero-list"></div>
                </div>
            </div>
        </div>

        <div class="table-card">
            <h3>Compare Countries</h3>
            <div style="position: relative; height: 300px; margin-bottom: 20px;">
                <canvas id="comparisonChart"></canvas>
            </div>
            <div style="border-top: 1px solid #2d3748; padding-top: 15px;">
                <h4 style="margin-bottom: 10px; color: #9ca3af; font-size: 12px;">Add/Remove Countries <button id="add-comparison-btn" style="float: right; background: #4ade80; color: #0f1419; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">+ Add</button></h4>
                <div id="comparison-inputs" style="display: flex; flex-wrap: wrap; gap: 10px;"></div>
            </div>
        </div>

        <div class="search-box">
            <h3 style="margin-bottom: 10px;">Search Country</h3>
            <input type="text" id="country-search" placeholder="Enter country code (e.g., us, gb, de)...">
            <div style="margin-top: 15px;">
                <canvas id="countryChart" style="max-height: 300px;"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        let totalChart, liveChart, top25Chart, distChart, regionChart, countryChart;
        let week1Chart, week2Chart, week3Chart, week4Chart;
        let refreshInterval, liveTickerInterval;
        let countryMap = {}; // Maps country names and codes to codes

        async function loadData() {
            const summary = await fetch('/api/summary').then(r => r.json());
            const networkTotal = await fetch('/api/network_total').then(r => r.json());
            const moversDetail = await fetch('/api/movers-detailed').then(r => r.json());

            // Build country name → code mapping from movers data
            if (moversDetail.gainers) {
                moversDetail.gainers.forEach(country => {
                    const code = country.code.toLowerCase();
                    countryMap[code] = code;
                    countryMap[country.name.toLowerCase()] = code;
                });
            }

            // Movers chart
            if (window.moversChartInst) window.moversChartInst.destroy();
            let gainers = (moversDetail.gainers || []).slice(0, 5);
            let losers = (moversDetail.losers || []).slice(0, 5);
            let moverLabels = [...gainers.map(g => g.code.toUpperCase()), ...losers.map(l => l.code.toUpperCase())];
            let moverData = [...gainers.map(g => g.deltas['24h']), ...losers.map(l => l.deltas['24h'])];
            let moverColors = [...gainers.map(g => '#4ade80'), ...losers.map(l => '#f87171')];
            window.moversChartInst = new Chart(document.getElementById('moversChart'), {
                type: 'bar',
                data: {
                    labels: moverLabels,
                    datasets: [{ label: '24h Change', data: moverData, backgroundColor: moverColors, borderRadius: 4 }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } }, x: { ticks: { color: '#9ca3af' }, grid: { display: false } } }
                }
            });

            // Populate Ticker
            if (moversDetail.gainers || moversDetail.losers) {
                const tickerContent = document.getElementById('ticker-content');
                let items = [];
                (moversDetail.gainers || []).slice(0, 15).forEach(m => {
                    if (m.deltas['1h'] > 0) items.push(`<span class="ticker-item gain">▲ ${m.code.toUpperCase()} +${m.deltas['1h']}</span>`);
                });
                (moversDetail.losers || []).slice(0, 15).forEach(m => {
                    if (m.deltas['1h'] < 0) items.push(`<span class="ticker-item loss">▼ ${m.code.toUpperCase()} ${m.deltas['1h']}</span>`);
                });
                // Duplicate items to ensure smooth infinite scroll
                if (tickerContent) tickerContent.innerHTML = items.join('') + items.join('');
            }

            // Add common country aliases
            const aliases = {
                'holland': 'nl', 'netherlands': 'nl',
                'uk': 'gb', 'england': 'gb', 'scotland': 'gb', 'wales': 'gb',
                'south korea': 'kr', 'korea': 'kr',
                'china': 'cn', 'prc': 'cn',
                'united states': 'us', 'usa': 'us', 'america': 'us',
                'united kingdom': 'gb',
                'hong kong': 'hk',
                'new zealand': 'nz',
                'south africa': 'za',
                'united arab emirates': 'ae', 'emirates': 'ae', 'dubai': 'ae',
                'czech republic': 'cz', 'czechia': 'cz',
                'costa rica': 'cr',
                'el salvador': 'sv',
            };
            for (const [alias, code] of Object.entries(aliases)) {
                if (countryMap[code]) countryMap[alias] = code;
            }
            const anomalies = await fetch('/api/anomalies?threshold=15').then(r => r.json()).catch(() => ({ anomalies: [] }));
            const growth = await fetch('/api/growth-projection').then(r => r.json()).catch(() => ({}));
            const regions = await fetch('/api/regions').then(r => r.json()).catch(() => ([]));
            const atRisk = await fetch('/api/at-risk').then(r => r.json()).catch(() => ({ disappeared: [], near_zero: [] }));

            // Handle anomalies - show all with delta and percentage
            const anomalyBanner = document.getElementById('anomaly-alert');
            if (anomalies.anomalies && anomalies.anomalies.length > 0) {
                const anomalyText = anomalies.anomalies.map(a => {
                    const sign = a.delta >= 0 ? '+' : '';
                    return `${a.country_name} ${sign}${a.delta} (${a.pct_change >= 0 ? '+' : ''}${a.pct_change.toFixed(1)}%)`;
                }).join('  •  ');
                document.getElementById('anomaly-text').textContent = anomalyText;
                anomalyBanner.classList.add('show');
            } else {
                anomalyBanner.classList.remove('show');
            }

            // Update growth projection
            if (growth.growth_rate !== undefined) {
                const rate = growth.growth_rate;
                document.getElementById('growth-rate').textContent = rate >= 0 ? `+${rate.toFixed(1)}%` : `${rate.toFixed(1)}%`;
                document.getElementById('growth-rate').style.color = rate >= 0 ? '#4ade80' : '#f87171';
                document.getElementById('projected-30d').textContent = (growth.projected_30d || 0).toLocaleString();
            }

            // Update stats
            document.getElementById('total').textContent = summary.total.toLocaleString();
            document.getElementById('top-country').textContent = summary.top_10[0]?.provider_count.toLocaleString() || '-';
            document.getElementById('top-country-code').textContent = summary.top_10[0]?.country_name || '-';

            const dayDelta = summary.day_delta;
            document.getElementById('day-delta').textContent = (dayDelta >= 0 ? '+' : '') + dayDelta.toLocaleString();
            document.getElementById('day-delta').className = dayDelta >= 0 ? 'delta-positive' : 'delta-negative';
            document.getElementById('day-delta-inline').textContent = (dayDelta >= 0 ? '+' : '') + dayDelta.toLocaleString();
            document.getElementById('day-delta-inline').className = dayDelta >= 0 ? 'delta-positive' : 'delta-negative';

            const hourDelta = summary.hour_delta;
            document.getElementById('hour-delta').textContent = (hourDelta >= 0 ? '+' : '') + hourDelta.toLocaleString();
            document.getElementById('hour-delta').className = hourDelta >= 0 ? 'delta-positive' : 'delta-negative';

            const weekDelta = summary.week_delta;
            document.getElementById('week-delta-inline').textContent = (weekDelta >= 0 ? '+' : '') + weekDelta.toLocaleString();
            document.getElementById('week-delta-inline').className = weekDelta >= 0 ? 'delta-positive' : 'delta-negative';

            // ATH / ATL badges
            if (summary.ath) {
                document.getElementById('ath-value').textContent = summary.ath.value.toLocaleString();
                const athDate = new Date(summary.ath.timestamp);
                document.getElementById('ath-date').textContent = athDate.toLocaleDateString('en-US', {month:'short', day:'numeric', year:'2-digit'});
            }
            if (summary.atl) {
                document.getElementById('atl-value').textContent = summary.atl.value.toLocaleString();
                const atlDate = new Date(summary.atl.timestamp);
                document.getElementById('atl-date').textContent = atlDate.toLocaleDateString('en-US', {month:'short', day:'numeric', year:'2-digit'});
            }

            // Live activity chart
            if (liveChart) liveChart.destroy();
            const liveN = 120; // 60 minutes at 30s
            let liveData = Array(liveN).fill(summary.total);
            let liveLabels = Array(liveN).fill('');
            liveChart = new Chart(document.getElementById('liveChart'), {
                type: 'line',
                data: {
                    labels: liveLabels,
                    datasets: [{
                        label: 'Live Total',
                        data: liveData,
                        borderColor: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.1)',
                        tension: 0.3,
                        fill: true,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    animation: { duration: 2000, easing: 'linear' },
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    scales: { y: { min: summary.total * 0.999, max: summary.total * 1.001, ticks: { display: false }, grid: { display: false } }, x: { display: false } }
                }
            });

            // Network total chart with MA + ATH/ATL reference lines
            if (totalChart) totalChart.destroy();
            const totalLabels = networkTotal.map(d => {
                const dt = new Date(d.timestamp);
                const h = dt.getHours() % 12 || 12;
                const min = dt.getMinutes().toString().padStart(2, '0');
                const short = `${dt.getMonth()+1}/${dt.getDate()} ${h}:${min}`;
                const full = `${dt.toLocaleDateString()} ${dt.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}`;
                return { short, full, timestamp: d.timestamp };
            });
            const n = networkTotal.length;
            const athDataset = summary.ath ? [{
                label: `ATH ${summary.ath.value.toLocaleString()}`,
                data: Array(n).fill(summary.ath.value),
                borderColor: 'rgba(245, 158, 11, 0.5)',
                borderDash: [4, 4],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                order: 10
            }] : [];
            const atlDataset = summary.atl ? [{
                label: `ATL ${summary.atl.value.toLocaleString()}`,
                data: Array(n).fill(summary.atl.value),
                borderColor: 'rgba(248, 113, 113, 0.45)',
                borderDash: [4, 4],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                order: 10
            }] : [];
            totalChart = new Chart(document.getElementById('totalChart'), {
                type: 'line',
                data: {
                    labels: totalLabels.map(l => l.short),
                    datasets: [{
                        label: 'Total Providers',
                        data: networkTotal.map(d => d.total),
                        borderColor: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.1)',
                        tension: 0.3,
                        fill: true,
                        pointRadius: 1,
                        pointHoverRadius: 5
                    }, {
                        label: '24h MA',
                        data: networkTotal.map(d => d.ma),
                        borderColor: '#9ca3af',
                        borderDash: [5, 5],
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: false
                    }, ...athDataset, ...atlDataset]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: true, labels: { color: '#9ca3af', filter: item => item.text !== '' } },
                        filler: { propagate: true },
                        tooltip: { callbacks: { title: ctx => totalLabels[ctx[0].dataIndex]?.full } }
                    },
                    scales: { y: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } }, x: { ticks: { color: '#9ca3af', maxTicksLimit: 24 }, grid: { display: false } } }
                }
            });

            // Mini weekly charts
            function drawMiniChart(chartVar, canvasId, sliceData, color) {
                if (chartVar) chartVar.destroy();
                if (!sliceData || sliceData.length === 0) return null;
                return new Chart(document.getElementById(canvasId), {
                    type: 'line',
                    data: {
                        labels: sliceData.map(d => {
                            let dt = new Date(d.timestamp);
                            return dt.toLocaleDateString([], {weekday: 'short', hour: '2-digit'});
                        }),
                        datasets: [{ data: sliceData.map(d => d.total), borderColor: color, borderWidth: 2, tension: 0.3, pointRadius: 0 }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: true } },
                        scales: { 
                            x: { display: true, ticks: { color: '#4a5568', font: {size: 9}, maxTicksLimit: 7 }, grid: { display: false } }, 
                            y: { display: true, position: 'right', ticks: { color: '#4a5568', font: {size: 9}, maxTicksLimit: 4 }, grid: { color: '#2d3748', borderDash: [2, 4] } } 
                        }
                    }
                });
            }
            week1Chart = drawMiniChart(week1Chart, 'week1Chart', networkTotal.slice(-168), '#4ade80');
            week2Chart = drawMiniChart(week2Chart, 'week2Chart', networkTotal.slice(-336, -168), '#60a5fa');
            week3Chart = drawMiniChart(week3Chart, 'week3Chart', networkTotal.slice(-504, -336), '#facc15');
            week4Chart = drawMiniChart(week4Chart, 'week4Chart', networkTotal.slice(-672, -504), '#f87171');

            // Top 10 bar chart
            if (top25Chart) top25Chart.destroy();
            top25Chart = new Chart(document.getElementById('top25Chart'), {
                type: 'bar',
                data: {
                    labels: summary.top_10.map(c => c.country_code.toUpperCase()),
                    datasets: [{
                        label: 'Providers',
                        data: summary.top_10.map(c => c.provider_count),
                        backgroundColor: '#4ade80'
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                afterLabel: function(ctx) {
                                    const r = regions[ctx.dataIndex];
                                    const sign = r.delta_24h >= 0 ? '+' : '';
                                    return `24h: ${sign}${r.delta_24h.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: { y: { ticks: { color: '#9ca3af' }, grid: { display: false } }, x: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } } }
                }
            });

            // Distribution donut chart
            if (distChart) distChart.destroy();
            const colors = [
                'rgba(96, 165, 250, 0.8)', 'rgba(245, 158, 11, 0.8)', 'rgba(74, 222, 128, 0.8)', 
                'rgba(248, 113, 113, 0.8)', 'rgba(167, 139, 250, 0.8)', 'rgba(20, 184, 166, 0.8)', 
                'rgba(251, 146, 60, 0.8)', 'rgba(249, 115, 22, 0.8)', 'rgba(6, 182, 212, 0.8)', 'rgba(139, 92, 246, 0.8)'
            ];
            distChart = new Chart(document.getElementById('distChart'), {
                type: 'doughnut',
                data: {
                    labels: summary.top_10.map(c => c.country_code.toUpperCase()),
                    datasets: [{
                        data: summary.top_10.map(c => c.provider_count),
                        backgroundColor: colors,
                        borderWidth: 0,
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '75%',
                    plugins: { legend: { position: 'right', labels: { color: '#e0e6ed', padding: 20, font: {size: 13} } } }
                }
            });

            // Regional chart
            if (regionChart) regionChart.destroy();
            const regionColors = regions.map(r => r.delta_24h >= 0 ? '#4ade80' : '#f87171');
            regionChart = new Chart(document.getElementById('regionChart'), {
                type: 'bar',
                data: {
                    labels: regions.map(r => r.region),
                    datasets: [{
                        label: 'Providers',
                        data: regions.map(r => r.total),
                        backgroundColor: regionColors,
                        minBarLength: 8
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                afterLabel: function(ctx) {
                                    const r = regions[ctx.dataIndex];
                                    const sign = r.delta_24h >= 0 ? '+' : '';
                                    return `24h: ${sign}${r.delta_24h.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: { y: { ticks: { color: '#9ca3af' }, grid: { display: false } }, x: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } } }
                }
            });

            // Populate at-risk lists
            document.getElementById('disappeared-list').innerHTML = atRisk.disappeared.length === 0 ? '<span style="color: #9ca3af;">None</span>' : atRisk.disappeared.map(c => `<div>${c.country_name} (had ${c.prev_count})</div>`).join('');
            document.getElementById('near-zero-list').innerHTML = atRisk.near_zero.length === 0 ? '<span style="color: #9ca3af;">None</span>' : atRisk.near_zero.map(c => {
                const delta = c.delta_24h || 0;
                return `<div>${c.country_name}: ${c.provider_count} (${delta >= 0 ? '+' : ''}${delta})</div>`;
            }).join('');

            // Update default comparison to show top 5 countries by provider count
            if (summary.top_10 && summary.top_10.length >= 5) {
                comparisonCountries = summary.top_10.slice(0, 5).map(c => c.country_code.toLowerCase());
                renderComparisonInputs();
                await updateComparison(); // Redraw the comparison chart with new countries
            }

            // Gainers and losers tables
            updateDetailedMoversTable('gainers-table', moversDetail.gainers);
            updateDetailedMoversTable('losers-table', moversDetail.losers);
        }
        
        async function updateDetailedMoversTable(tableId, data) {
            const windows = ['15m', '1h', '2h', '3h', '6h', '12h', '24h', '2d', '3d', '4d', '5d', '6d', '7d', '14d', '30d'];
            const tbody = document.querySelector(`#${tableId} tbody`);

            tbody.innerHTML = await Promise.all(data.map(async (row) => {
                const deltaColumns = windows.map(w => {
                    const delta = row.deltas[w] || 0;
                    const color = delta >= 0 ? '#4ade80' : delta < 0 ? '#f87171' : '#9ca3af';
                    return `<td style="color: ${color}; ${w === '24h' ? 'font-weight:bold;background:rgba(74,222,128,0.08)' : ''}">${(delta >= 0 ? '+' : '') + delta.toLocaleString()}</td>`;
                }).join('');

                let stats = '';
                try {
                    const resp = await fetch(`/api/country-stats/${row.code.toLowerCase()}`);
                    const s = await resp.json();
                    const vol_color = s.volatility === 'high' ? '#f87171' : s.volatility === 'medium' ? '#facc15' : '#4ade80';
                    stats = `<span class="volatility" style="color: ${vol_color};" title="Churn: ${s.churn_rate}/h">${s.volatility} (${s.churn_rate}/h)</span>`;
                } catch(e) {}

                return `
                    <tr>
                        <td>${row.name} ${stats}</td>
                        <td>${row.current.toLocaleString()}</td>
                        ${deltaColumns}
                    </tr>
                `;
            })).then(rows => rows.join(''));
        }
        
        document.getElementById('country-search').addEventListener('keypress', async (e) => {
            if (e.key === 'Enter') {
                const code = e.target.value.toLowerCase();
                const data = await fetch(`/api/country/${code}`).then(r => r.json());
                if (countryChart) countryChart.destroy();
                countryChart = new Chart(document.getElementById('countryChart'), {
                    type: 'line',
                    data: {
                        labels: data.map(d => new Date(d.timestamp).toLocaleString()),
                        datasets: [{
                            label: code.toUpperCase(),
                            data: data.map(d => d.count),
                            borderColor: '#60a5fa',
                            fill: false
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { labels: { color: '#9ca3af' } } },
                        scales: { y: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } }, x: { ticks: { color: '#9ca3af' }, grid: { display: false } } }
                    }
                });
            }
        });

        let comparisonChart;
        let comparisonCountries = ['us', 'de'];
        const colors = ['#60a5fa', '#f59e0b', '#4ade80', '#f87171', '#a78bfa', '#14b8a6'];

        document.getElementById('add-comparison-btn').addEventListener('click', () => {
            comparisonCountries.push('');
            renderComparisonInputs();
            // Focus on the newly added input (the one with empty value at the last index)
            const newIdx = comparisonCountries.length - 1;
            document.querySelector(`.comp-input[data-idx="${newIdx}"]`)?.focus();
        });

        function resolveCountryCode(input) {
            const lower = input.toLowerCase().trim();
            // If it's already a valid code (2 chars), check if it's valid
            if (lower.length === 2 && countryMap[lower]) return countryMap[lower];
            // Try to find by country name
            if (countryMap[lower]) return countryMap[lower];
            // Return as-is if not found (for fuzzy matching or user error)
            return lower;
        }

        function renderComparisonInputs() {
            const container = document.getElementById('comparison-inputs');
            container.innerHTML = comparisonCountries.map((code, idx) => {
                const displayCode = code.length === 2 ? code : '';
                return `
                <div style="background: #1a1f26; border: 1px solid #2d3748; padding: 10px; border-radius: 4px; display: flex; gap: 5px; align-items: center;">
                    <input type="text" class="comp-input" data-idx="${idx}" value="${displayCode}" placeholder="e.g., us or United States" maxlength="40" style="width: 140px;">
                    <button class="remove-comp" data-idx="${idx}" style="background: #f87171; color: white; border: none; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 10px;">Remove</button>
                </div>
            `;
            }).join('');

            container.querySelectorAll('.comp-input').forEach(inp => {
                inp.addEventListener('change', (e) => {
                    const resolved = resolveCountryCode(e.target.value);
                    comparisonCountries[parseInt(e.target.dataset.idx)] = resolved;
                    // Update display to show the code
                    if (resolved.length === 2) e.target.value = resolved;
                    updateComparison();
                });
            });
            container.querySelectorAll('.remove-comp').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    comparisonCountries.splice(parseInt(e.target.dataset.idx), 1);
                    renderComparisonInputs();
                    updateComparison();
                });
            });
        }

        async function updateComparison() {
            const validCodes = comparisonCountries.filter(c => c.length === 2);
            if (validCodes.length < 2) return;

            const allData = {};
            for (let code of validCodes) {
                const resp = await fetch(`/api/country/${code}`).catch(() => null);
                if (resp) allData[code] = await resp.json();
            }

            if (!Object.keys(allData).length) return;

            const allTs = [...new Set(Object.values(allData).flat().map(d => d.timestamp))].sort();
            if (comparisonChart) comparisonChart.destroy();

            const datasets = validCodes.map((code, idx) => ({
                label: code.toUpperCase(),
                data: allTs.map(t => {
                    const entry = (allData[code] || []).find(x => x.timestamp === t);
                    return entry ? entry.count : null;
                }),
                borderColor: colors[idx % colors.length],
                fill: false,
                tension: 0.3
            }));

            comparisonChart = new Chart(document.getElementById('comparisonChart'), {
                type: 'line',
                data: {
                    labels: allTs.map(t => {
                        const d = new Date(t);
                        const date = d.toLocaleDateString();
                        const time = d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
                        return `${date} ${time}`;
                    }),
                    datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#9ca3af' } } },
                    scales: { y: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } }, x: { ticks: { color: '#9ca3af' }, grid: { display: false } } }
                }
            });
        }

        renderComparisonInputs();

        async function pollLiveTotal() {
            try {
                const live = await fetch('/api/live_total').then(r => r.json());
                if (liveChart) {
                    const dataArr = liveChart.data.datasets[0].data;
                    const labelsArr = liveChart.data.labels;
                    
                    let jitter = Math.floor(Math.random() * 9) - 4; // -4 to +4
                    let point = live.total + jitter;
                    dataArr.push(point);
                    labelsArr.push('');
                    
                    if (dataArr.length > 120) {
                        dataArr.shift();
                        labelsArr.shift();
                    }
                    
                    // Adjust y-axis bounds dynamically
                    const minVal = Math.min(...dataArr);
                    const maxVal = Math.max(...dataArr);
                    liveChart.options.scales.y.min = minVal === maxVal ? minVal * 0.999 : minVal * 0.999;
                    liveChart.options.scales.y.max = minVal === maxVal ? maxVal * 1.001 : maxVal * 1.001;
                    
                    liveChart.update();
                }
            } catch (e) {}
        }

        function startRefreshTimer() {
            let seconds = 300;
            refreshInterval = setInterval(() => {
                seconds--;
                const mins = Math.floor(seconds / 60);
                const secs = seconds % 60;
                document.getElementById('refresh-timer').textContent = `${mins}m ${secs}s`;
                if (seconds <= 0) {
                    loadData();
                    seconds = 300;
                }
            }, 1000);
            
            // 30 second polling for live total chart
            liveTickerInterval = setInterval(pollLiveTotal, 30000);
        }
        
        loadData();
        updateComparison(); // Initialize default comparison chart
        startRefreshTimer();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
