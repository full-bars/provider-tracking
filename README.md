# Provider Tracking Dashboard

Real-time monitoring and analytics dashboard for URnetwork provider metrics across global regions.

## Features

- **Real-time Network Monitoring** — Live provider count tracking with hourly snapshots
- **Anomaly Detection** — Automatic detection of >15% provider count changes (configurable threshold)
- **Regional Analysis** — 6-region aggregation (North America, Europe, Asia-Pacific, Middle East, South America, Africa) with 24-hour deltas
- **Growth Analytics** — Daily growth rate projections with 30-day trends and volatility indicators
- **At-Risk Tracking** — Identifies countries losing providers and near-zero capacity regions
- **Multi-Country Comparison** — Dynamic side-by-side analysis of up to 10 providers simultaneously
- **Moving Averages** — 24-hour rolling average overlaid on network total trends
- **Historical Data** — Up to 7 days of historical snapshots for trend analysis

## Tech Stack

- **Backend** — Python Flask with SQLite (primary), or Rust with Actix-web (experimental)
- **Frontend** — Vanilla JavaScript with Chart.js for visualizations
- **Data Collection** — Hourly URnetwork API polling
- **Deployment** — systemd service on Linux
- **Reverse Proxy** — Caddy for HTTPS and multi-domain routing

## Installation

### Prerequisites
- Python 3.9+
- SQLite3

### Setup

1. Clone the repository:
```bash
git clone https://github.com/full-bars/provider-tracking.git
cd provider-tracking
```

2. Create database directory:
```bash
mkdir -p ~/provider_tracking
```

3. Initialize the database schema:
```bash
sqlite3 ~/provider_tracking/providers.db < schema.sql
```

4. Set up data collection via cron:
```bash
0 * * * * /path/to/poll_providers.sh >> /var/log/provider-tracking.log 2>&1
```

5. Configure and start the dashboard service:
```bash
# Copy systemd service file
sudo cp provider-dashboard.service /etc/systemd/system/

# Enable and start
sudo systemctl enable provider-dashboard
sudo systemctl start provider-dashboard
```

The dashboard is then available at `http://localhost:5000`

## Usage

### Web Dashboard

Access the interactive dashboard at `http://<server>:5000` to view:
- **Network Summary** — Total provider count, hourly/daily deltas
- **Top 10 Countries** — Bar chart of highest-capacity regions
- **Regional Breakdown** — Horizontal stacked bar chart with 24h change indicators
- **Network Trend** — 7-day line chart with 24h moving average overlay
- **Distribution** — Donut chart showing top 10 + "Others" concentration
- **Anomalies** — Real-time alert banner for significant changes (>15% by default)
- **Gainers/Losers** — 24h movers table with volatility scores
- **At-Risk Countries** — Tracking disappeared and near-zero capacity providers

### Customization

**Anomaly Threshold** — Adjust detection sensitivity in the dashboard:
- Input field next to anomaly banner (default: 15%)
- Value persisted to browser localStorage
- Automatically re-fetches and updates alerts

**Time Range Buttons** — View movers and trends across:
- Last 1 hour
- Last 24 hours
- Last 7 days

## API Endpoints

### `/api/summary`
Current network state with top 10 countries.
```json
{
  "timestamp": "2026-05-24T22:15:00",
  "total": 65459,
  "hour_delta": 120,
  "day_delta": -2000,
  "top_10": [...]
}
```

### `/api/network_total`
Hourly totals with 24h moving average (past 168 hours).
```json
[
  {
    "timestamp": "2026-05-24T21:00:00",
    "total": 65340,
    "ma": 64800
  }
]
```

### `/api/movers`
Gainers and losers by time window (1h, 24h, 7d).

### `/api/regions`
Regional aggregation with 24h deltas.
```json
[
  {
    "region": "North America",
    "total": 22000,
    "delta_24h": -500
  }
]
```

### `/api/at-risk`
Countries that disappeared (0 providers) or near-zero (1–5 providers).
```json
{
  "disappeared": [...],
  "near_zero": [...]
}
```

### `/api/anomalies`
Significant movers above threshold.
```
?threshold=15  (percentage, optional)
```

## Data Collection

The `poll_providers.sh` script runs hourly and:
1. Authenticates with URnetwork API using JWT from `~/.urnetwork/jwt`
2. Fetches provider locations via `/api/network/provider-locations`
3. Aggregates counts by country_code and country_name
4. Inserts snapshot with current timestamp into database

Run manually:
```bash
./poll_providers.sh
```

## Database Schema

```sql
CREATE TABLE provider_counts (
  id INTEGER PRIMARY KEY,
  timestamp TEXT NOT NULL,
  country_code TEXT NOT NULL,
  country_name TEXT NOT NULL,
  provider_count INTEGER NOT NULL,
  UNIQUE(timestamp, country_code)
);
```

## Architecture

### Data Flow
1. **Collection** — `poll_providers.sh` → URnetwork API
2. **Storage** — SQLite database with hourly snapshots
3. **API** — Flask REST endpoints aggregate and compute deltas
4. **Frontend** — Chart.js visualizations with client-side interactivity

### Key Calculations
- **Moving Average** — 24-point rolling average of network totals
- **Anomalies** — (current - past) / past > threshold, absolute value
- **Regional Totals** — SUM(provider_count) grouped by REGIONS mapping
- **Growth Rate** — (current_total - 30d_ago) / 30d_ago * 100
- **Volatility** — Std dev of 24h deltas

## Deployment

Deploy to LA1 server:
```bash
scp dashboard/app.py user@100.70.15.86:/home/user/provider_tracking/dashboard/app.py
ssh user@100.70.15.86 'sudo systemctl restart provider-dashboard'
```

## Development

Run locally:
```bash
cd dashboard
python3 app.py
```

Server runs on `http://localhost:5000` with auto-reload disabled (edit `app.run()` to enable debug mode).

## Rust Backend (Experimental)

A high-performance Rust reimplementation is available in `backend-rs/` using Actix-web and async SQLx. The Rust backend provides identical API compatibility with lower memory footprint and higher throughput.

### Building

```bash
cd backend-rs
cargo build --release
```

Binary output: `target/release/provider_tracker` (~9.8 MB)

### Running Rust Backend

Set DATABASE_URL environment variable (optional, defaults to `~/provider_tracking/providers.db`):

```bash
DATABASE_URL="sqlite:///path/to/providers.db" ./target/release/provider_tracker
```

Server runs on `http://0.0.0.0:5001`

### Deployment

Deploy to LA1 alongside Python version:

```bash
scp backend-rs/target/release/provider_tracker user@100.70.15.86:/home/user/provider_tracking/
scp provider-dashboard-rs.service user@100.70.15.86:/tmp/
ssh user@100.70.15.86 'sudo mv /tmp/provider-dashboard-rs.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable provider-dashboard-rs && sudo systemctl start provider-dashboard-rs'
```

Update Caddy configuration to route subdomain:

```
provider-rs.urnetwork.mywire.org {
	reverse_proxy localhost:5001
}
```

Both Flask (port 5000) and Rust (port 5001) versions can run simultaneously, sharing the same SQLite database.

## License

Private repository
