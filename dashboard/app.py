#!/usr/bin/env python3
from flask import Flask, jsonify, render_template_string
from datetime import datetime, timedelta
import sqlite3
import json
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path.home() / "provider_tracking" / "providers.db"

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
        WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1
    """, (hour_ago,))
    hour_ago_total = cursor.fetchone()['total'] or current_total
    hour_delta = current_total - hour_ago_total
    
    # Day-over-day delta
    day_ago = (datetime.fromisoformat(latest) - timedelta(days=1)).isoformat(sep=' ')
    cursor.execute("""
        SELECT SUM(provider_count) as total FROM provider_counts 
        WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1
    """, (day_ago,))
    day_ago_total = cursor.fetchone()['total'] or current_total
    day_delta = current_total - day_ago_total
    
    # Top 10
    cursor.execute("""
        SELECT country_name, country_code, provider_count 
        FROM provider_counts WHERE timestamp = ? 
        ORDER BY provider_count DESC LIMIT 10
    """, (latest,))
    top_10 = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({
        'timestamp': latest,
        'total': current_total,
        'hour_delta': hour_delta,
        'day_delta': day_delta,
        'top_10': top_10
    })

@app.route('/api/network_total')
def api_network_total():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, SUM(provider_count) as total 
        FROM provider_counts 
        GROUP BY timestamp 
        ORDER BY timestamp DESC LIMIT 168
    """)
    data = [{'timestamp': row[0], 'total': row[1]} for row in cursor.fetchall()]
    data.reverse()
    
    conn.close()
    return jsonify(data)

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

    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]
    hour_ago = (datetime.fromisoformat(latest) - timedelta(hours=1)).isoformat(sep=' ')

    cursor.execute("""
        WITH current AS (
            SELECT country_code, country_name, provider_count
            FROM provider_counts WHERE timestamp = ?
        ),
        past AS (
            SELECT country_code, provider_count
            FROM provider_counts
            WHERE timestamp = (
                SELECT MAX(timestamp) FROM provider_counts WHERE timestamp <= ?
            )
        )
        SELECT c.country_name, c.country_code, c.provider_count,
               COALESCE(c.provider_count - p.provider_count, 0) as delta,
               CASE WHEN p.provider_count > 0
                    THEN CAST(c.provider_count - p.provider_count AS FLOAT) / p.provider_count * 100
                    ELSE 0 END as pct_change
        FROM current c
        LEFT JOIN past p ON c.country_code = p.country_code
        WHERE CAST(c.provider_count - p.provider_count AS FLOAT) / NULLIF(p.provider_count, 0) < -0.15
        ORDER BY pct_change ASC
    """, (latest, hour_ago))

    anomalies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'anomalies': anomalies, 'threshold': -0.15})

@app.route('/api/growth-projection')
def api_growth_projection():
    conn = get_db()
    cursor = conn.cursor()

    latest = cursor.execute("SELECT MAX(timestamp) FROM provider_counts").fetchone()[0]
    day_ago = (datetime.fromisoformat(latest) - timedelta(days=1)).isoformat(sep=' ')

    cursor.execute("SELECT SUM(provider_count) as total FROM provider_counts WHERE timestamp = ?", (latest,))
    current = cursor.fetchone()['total']

    cursor.execute("SELECT SUM(provider_count) as total FROM provider_counts WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1", (day_ago,))
    past = cursor.fetchone()['total'] or current

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
        '7d': 10080
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
        ORDER BY timestamp DESC LIMIT 168
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
        .alert-banner { background: #7f1d1d; border: 1px solid #991b1b; color: #fecaca; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: none; }
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Provider Network Dashboard</h1>

        <div class="alert-banner" id="anomaly-alert">
            <strong>⚠️ Anomaly Detected:</strong> <span id="anomaly-text"></span>
        </div>

        <div class="controls">
            <span style="font-size: 12px; color: #9ca3af;">Time Range:</span>
            <button class="toggle-btn active" data-range="24h">Last 24h</button>
            <button class="toggle-btn" data-range="7d">Last 7d</button>
            <button class="toggle-btn" data-range="30d">Last 30d</button>
        </div>

        <div class="header" id="header">
            <div class="stat-card">
                <div class="stat-value" id="total">-</div>
                <div class="stat-label">Total Network Providers</div>
                <div class="stat-delta"><span id="day-delta">-</span> (24h)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="top-country">-</div>
                <div class="stat-label">Largest Country</div>
                <div class="stat-delta" id="top-country-code">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="hour-delta">-</div>
                <div class="stat-label">Change (1h)</div>
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
                <h3>Network Total Over Time</h3>
                <div class="chart-container"><canvas id="totalChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3>Top 10 Countries</h3>
                <div class="chart-container"><canvas id="top10Chart"></canvas></div>
            </div>
        </div>
        
        <div class="table-card">
            <h3>Top 50 Gainers (24h)</h3>
            <table id="gainers-table" style="font-size: 12px;">
                <thead><tr><th>Country</th><th>Current</th><th>15m Δ</th><th>1h Δ</th><th>2h Δ</th><th>3h Δ</th><th>6h Δ</th><th>12h Δ</th><th>24h Δ</th><th>2d Δ</th><th>3d Δ</th><th>4d Δ</th><th>5d Δ</th><th>6d Δ</th><th>7d Δ</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>

        <div class="table-card">
            <h3>Top 50 Losers (24h)</h3>
            <table id="losers-table" style="font-size: 12px;">
                <thead><tr><th>Country</th><th>Current</th><th>15m Δ</th><th>1h Δ</th><th>2h Δ</th><th>3h Δ</th><th>6h Δ</th><th>12h Δ</th><th>24h Δ</th><th>2d Δ</th><th>3d Δ</th><th>4d Δ</th><th>5d Δ</th><th>6d Δ</th><th>7d Δ</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>
        
        <div class="search-box">
            <h3 style="margin-bottom: 10px;">Search Country</h3>
            <input type="text" id="country-search" placeholder="Enter country code (e.g., us, gb, de)...">
            <div style="margin-top: 15px;">
                <canvas id="countryChart" style="max-height: 300px;"></canvas>
            </div>
        </div>

        <div class="table-card">
            <h3>Compare Countries <button id="add-comparison-btn" style="float: right; background: #4ade80; color: #0f1419; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">+ Add Country</button></h3>
            <div id="comparison-inputs" style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;"></div>
            <div style="position: relative; height: 300px;">
                <canvas id="comparisonChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        let totalChart, top10Chart, countryChart;
        let refreshInterval;
        
        async function loadData() {
            const summary = await fetch('/api/summary').then(r => r.json());
            const networkTotal = await fetch('/api/network_total').then(r => r.json());
            const moversDetail = await fetch('/api/movers-detailed').then(r => r.json());
            const anomalies = await fetch('/api/anomalies').then(r => r.json()).catch(() => ({ anomalies: [] }));
            const growth = await fetch('/api/growth-projection').then(r => r.json()).catch(() => ({}));

            // Handle anomalies
            const anomalyBanner = document.getElementById('anomaly-alert');
            if (anomalies.anomalies && anomalies.anomalies.length > 0) {
                const top = anomalies.anomalies[0];
                document.getElementById('anomaly-text').textContent = `${top.country_name} lost ${Math.abs(top.pct_change).toFixed(1)}% providers in 1h`;
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
            
            const hourDelta = summary.hour_delta;
            document.getElementById('hour-delta').textContent = (hourDelta >= 0 ? '+' : '') + hourDelta.toLocaleString();
            document.getElementById('hour-delta').className = hourDelta >= 0 ? 'delta-positive' : 'delta-negative';
            
            // Network total chart
            if (totalChart) totalChart.destroy();
            totalChart = new Chart(document.getElementById('totalChart'), {
                type: 'line',
                data: {
                    labels: networkTotal.map(d => new Date(d.timestamp).toLocaleDateString()),
                    datasets: [{
                        label: 'Total Providers',
                        data: networkTotal.map(d => d.total),
                        borderColor: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.05)',
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, filler: { propagate: true } },
                    scales: { y: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } }, x: { ticks: { color: '#9ca3af' }, grid: { display: false } } }
                }
            });
            
            // Top 10 chart
            if (top10Chart) top10Chart.destroy();
            top10Chart = new Chart(document.getElementById('top10Chart'), {
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
                    plugins: { legend: { display: false } },
                    scales: { y: { ticks: { color: '#9ca3af' }, grid: { display: false } }, x: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3748' } } }
                }
            });
            
            // Gainers and losers tables
            updateDetailedMoversTable('gainers-table', moversDetail.gainers);
            updateDetailedMoversTable('losers-table', moversDetail.losers);
        }
        
        async function updateDetailedMoversTable(tableId, data) {
            const windows = ['15m', '1h', '2h', '3h', '6h', '12h', '24h', '2d', '3d', '4d', '5d', '6d', '7d'];
            const tbody = document.querySelector(`#${tableId} tbody`);

            tbody.innerHTML = await Promise.all(data.map(async (row) => {
                const deltaColumns = windows.map(w => {
                    const delta = row.deltas[w] || 0;
                    const color = delta >= 0 ? '#4ade80' : delta < 0 ? '#f87171' : '#9ca3af';
                    return `<td style="color: ${color}">${(delta >= 0 ? '+' : '') + delta.toLocaleString()}</td>`;
                }).join('');

                let stats = '';
                try {
                    const resp = await fetch(`/api/country-stats/${row.code.toLowerCase()}`);
                    const s = await resp.json();
                    const vol_color = s.volatility === 'high' ? '#f87171' : s.volatility === 'medium' ? '#facc15' : '#4ade80';
                    stats = `<span class="volatility" style="color: ${vol_color};" title="Churn: ${s.churn_rate}/h">${s.volatility}</span>`;
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
            const input = document.createElement('div');
            input.style.cssText = 'background: #1a1f26; border: 1px solid #2d3748; padding: 10px; border-radius: 4px; display: flex; gap: 5px; align-items: center;';
            const idx = comparisonCountries.length;
            input.innerHTML = `
                <input type="text" class="comp-input" data-idx="${idx}" placeholder="e.g., us" maxlength="2" style="max-width: 60px;">
                <button class="remove-comp" style="background: #f87171; color: white; border: none; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 10px;">Remove</button>
            `;
            document.getElementById('comparison-inputs').appendChild(input);
            input.querySelector('.comp-input').addEventListener('change', updateComparison);
            input.querySelector('.remove-comp').addEventListener('click', () => {
                comparisonCountries.splice(idx, 1);
                input.remove();
                updateComparison();
            });
        });

        function renderComparisonInputs() {
            const container = document.getElementById('comparison-inputs');
            container.innerHTML = comparisonCountries.map((code, idx) => `
                <div style="background: #1a1f26; border: 1px solid #2d3748; padding: 10px; border-radius: 4px; display: flex; gap: 5px; align-items: center;">
                    <input type="text" class="comp-input" data-idx="${idx}" value="${code}" maxlength="2" style="max-width: 60px;">
                    <button class="remove-comp" data-idx="${idx}" style="background: #f87171; color: white; border: none; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 10px;">Remove</button>
                </div>
            `).join('');

            container.querySelectorAll('.comp-input').forEach(inp => {
                inp.addEventListener('change', (e) => {
                    comparisonCountries[parseInt(e.target.dataset.idx)] = e.target.value.toLowerCase();
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
                    labels: allTs.map(t => new Date(t).toLocaleDateString()),
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

        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
        
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
        }
        
        loadData();
        startRefreshTimer();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
