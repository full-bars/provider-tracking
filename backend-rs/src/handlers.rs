use actix_web::{web, HttpResponse};
use serde_json::json;
use chrono::Duration;
use std::collections::HashMap;

use crate::{AppState, models::*, db, regions};

pub async fn api_summary(state: web::Data<AppState>) -> HttpResponse {
    let pool = &state.pool;
    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let current_total = match db::get_total_at_timestamp(pool, &latest).await {
        Ok(Some(total)) => total,
        Ok(None) => 0,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let hour_ago = format_time_offset(&latest, -60);
    let hour_ago_total = db::get_total_at_timestamp(pool, &hour_ago).await.unwrap_or(None).unwrap_or(current_total);
    let hour_delta = current_total - hour_ago_total;

    let day_ago = format_time_offset(&latest, -1440);
    let day_ago_total = db::get_total_at_timestamp(pool, &day_ago).await.unwrap_or(None).unwrap_or(current_total);
    let day_delta = current_total - day_ago_total;

    let week_ago = format_time_offset(&latest, -10080);
    let week_ago_total = db::get_total_at_timestamp(pool, &week_ago).await.unwrap_or(None).unwrap_or(current_total);
    let week_delta = current_total - week_ago_total;
    let two_week_ago = format_time_offset(&latest, -20160);
    let month_ago = format_time_offset(&latest, -43200);

    let top_10 = match db::get_top_countries(pool, &latest, 10).await {
        Ok(countries) => countries,
        Err(_) => vec![],
    };

    let (hour_high, hour_low) = db::get_network_range(pool, &hour_ago, &latest).await.unwrap_or((0, 0));
    let (day_high, day_low) = db::get_network_range(pool, &day_ago, &latest).await.unwrap_or((0, 0));
    let (week_high, week_low) = db::get_network_range(pool, &week_ago, &latest).await.unwrap_or((0, 0));
    let (two_week_high, two_week_low) = db::get_network_range(pool, &two_week_ago, &latest).await.unwrap_or((0, 0));
    let (month_high, month_low) = db::get_network_range(pool, &month_ago, &latest).await.unwrap_or((0, 0));

    let response = SummaryResponse {
        timestamp: latest,
        total: current_total,
        hour_delta,
        day_delta,
        week_delta,
        top_10,
        hour_range: (hour_low, hour_high),
        day_range: (day_low, day_high),
        week_range: (week_low, week_high),
        two_week_range: (two_week_low, two_week_high),
        month_range: (month_low, month_high),
    };

    HttpResponse::Ok().json(response)
}

pub async fn api_network_total(state: web::Data<AppState>) -> HttpResponse {
    let pool = &state.pool;
    match db::get_network_totals(pool, 720).await {
        Ok(data) => HttpResponse::Ok().json(data),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

pub async fn api_regions(state: web::Data<AppState>) -> HttpResponse {
    let pool = &state.pool;
    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let day_ago = format_time_offset(&latest, -1440);
    let current_countries = match db::get_countries_at_timestamp(pool, &latest).await {
        Ok(countries) => countries,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let mut region_totals: HashMap<&'static str, (i32, i32)> = HashMap::new();

    for cc in current_countries.iter() {
        let region = regions::get_region(&cc.country_code);
        let entry = region_totals.entry(region).or_insert((0, 0));
        entry.0 += cc.provider_count;

        if let Ok(Some(past_count)) = db::get_country_at_time(pool, &cc.country_code, &day_ago).await {
            entry.1 += cc.provider_count - past_count;
        }
    }

    let mut result: Vec<Region> = region_totals
        .into_iter()
        .map(|(region, (total, delta))| Region {
            region: region.to_string(),
            total,
            delta_24h: delta,
        })
        .collect();

    result.sort_by(|a, b| b.total.cmp(&a.total));
    HttpResponse::Ok().json(result)
}

pub async fn api_at_risk(state: web::Data<AppState>) -> HttpResponse {
    let pool = &state.pool;
    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let day_ago = format_time_offset(&latest, -1440);
    let current_countries = match db::get_countries_at_timestamp(pool, &latest).await {
        Ok(countries) => countries,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let mut disappeared = Vec::new();
    let mut near_zero = Vec::new();

    for cc in current_countries.iter() {
        if cc.provider_count == 0 {
            if let Ok(Some(past)) = db::get_country_at_time(pool, &cc.country_code, &day_ago).await {
                if past > 0 {
                    disappeared.push(CountryCount {
                        country_code: cc.country_code.clone(),
                        country_name: cc.country_name.clone(),
                        provider_count: cc.provider_count,
                    });
                }
            }
        } else if cc.provider_count >= 1 && cc.provider_count <= 5 {
            if let Ok(Some(past)) = db::get_country_at_time(pool, &cc.country_code, &day_ago).await {
                if cc.provider_count < past {
                    near_zero.push(CountryCount {
                        country_code: cc.country_code.clone(),
                        country_name: cc.country_name.clone(),
                        provider_count: cc.provider_count,
                    });
                }
            }
        }
    }

    HttpResponse::Ok().json(json!({
        "disappeared": disappeared,
        "near_zero": near_zero
    }))
}

pub async fn api_anomalies(state: web::Data<AppState>, query: web::Query<HashMap<String, String>>) -> HttpResponse {
    let pool = &state.pool;
    let threshold_pct: f64 = query
        .get("threshold")
        .and_then(|s| s.parse().ok())
        .unwrap_or(15.0);
    let threshold = threshold_pct / 100.0;

    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let hour_ago = format_time_offset(&latest, -60);

    match db::get_anomalies(pool, &latest, &hour_ago, threshold).await {
        Ok((gains, losses)) => {
            let combined: Vec<_> = gains
                .into_iter()
                .chain(losses)
                .collect();
            
            let response = combined.iter().map(|a| json!({
                "country_code": a.country_code,
                "country_name": a.country_name,
                "provider_count": a.provider_count,
                "delta": a.delta,
                "pct_change": a.percent_change
            })).collect::<Vec<_>>();

            HttpResponse::Ok().json(json!({"anomalies": response, "threshold": threshold_pct}))
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

pub async fn api_movers(state: web::Data<AppState>) -> HttpResponse {
    let pool = &state.pool;
    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let hour_ago = format_time_offset(&latest, -60);
    let day_ago = format_time_offset(&latest, -1440);
    let week_ago = format_time_offset(&latest, -10080);

    let (hour_gainers, hour_losers) = db::get_movers(pool, &hour_ago, &latest).await.unwrap_or((vec![], vec![]));
    let (day_gainers, day_losers) = db::get_movers(pool, &day_ago, &latest).await.unwrap_or((vec![], vec![]));
    let (week_gainers, week_losers) = db::get_movers(pool, &week_ago, &latest).await.unwrap_or((vec![], vec![]));

    let response = json!({
        "1h": {"gainers": hour_gainers, "losers": hour_losers},
        "24h": {"gainers": day_gainers, "losers": day_losers},
        "7d": {"gainers": week_gainers, "losers": week_losers}
    });

    HttpResponse::Ok().json(response)
}

pub async fn api_movers_detailed(state: web::Data<AppState>) -> HttpResponse {
    let pool = &state.pool;
    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let windows = vec![
        ("15m", 15),
        ("1h", 60),
        ("2h", 120),
        ("3h", 180),
        ("6h", 360),
        ("12h", 720),
        ("24h", 1440),
        ("2d", 2880),
        ("3d", 4320),
        ("4d", 5760),
        ("5d", 7200),
        ("6d", 8640),
        ("7d", 10080),
    ];

    let current_countries = match db::get_countries_at_timestamp(pool, &latest).await {
        Ok(c) => c,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let mut country_data: HashMap<String, serde_json::Value> = HashMap::new();

    for cc in current_countries.iter() {
        let mut deltas = HashMap::new();

        for (window_name, minutes) in windows.iter() {
            let past_time = format_time_offset(&latest, -(*minutes as i32));
            let delta = match db::get_country_at_time(pool, &cc.country_code, &past_time).await {
                Ok(Some(past_count)) => cc.provider_count - past_count,
                _ => 0,
            };
            deltas.insert(window_name.to_string(), delta);
        }

        country_data.insert(
            cc.country_code.clone(),
            json!({
                "code": cc.country_code,
                "name": cc.country_name,
                "current": cc.provider_count,
                "deltas": deltas
            }),
        );
    }

    // Get top 50 gainers (largest positive delta, sorted by country code for stability)
    let mut gainers_vec: Vec<_> = country_data.values().cloned().collect();
    gainers_vec.sort_by(|a, b| {
        let delta_a = a.get("deltas").and_then(|d| d.get("24h")).and_then(|v| v.as_i64()).unwrap_or(0);
        let delta_b = b.get("deltas").and_then(|d| d.get("24h")).and_then(|v| v.as_i64()).unwrap_or(0);
        match delta_b.cmp(&delta_a) {
            std::cmp::Ordering::Equal => {
                let code_a = a.get("code").and_then(|v| v.as_str()).unwrap_or("");
                let code_b = b.get("code").and_then(|v| v.as_str()).unwrap_or("");
                code_a.cmp(code_b)
            }
            other => other,
        }
    });
    let gainers: Vec<_> = gainers_vec.into_iter().take(50).collect();

    // Get top 50 losers (smallest negative delta, sorted by country code for stability)
    let mut losers_vec: Vec<_> = country_data.values().cloned().collect();
    losers_vec.sort_by(|a, b| {
        let delta_a = a.get("deltas").and_then(|d| d.get("24h")).and_then(|v| v.as_i64()).unwrap_or(0);
        let delta_b = b.get("deltas").and_then(|d| d.get("24h")).and_then(|v| v.as_i64()).unwrap_or(0);
        match delta_a.cmp(&delta_b) {
            std::cmp::Ordering::Equal => {
                let code_a = a.get("code").and_then(|v| v.as_str()).unwrap_or("");
                let code_b = b.get("code").and_then(|v| v.as_str()).unwrap_or("");
                code_a.cmp(code_b)
            }
            other => other,
        }
    });
    let losers: Vec<_> = losers_vec.into_iter().take(50).collect();

    HttpResponse::Ok().json(json!({"gainers": gainers, "losers": losers}))
}

pub async fn api_country_stats(state: web::Data<AppState>, path: web::Path<String>) -> HttpResponse {
    let pool = &state.pool;
    let code = path.into_inner();

    let data = match db::get_country_history(pool, &code, 24).await {
        Ok(d) => d,
        Err(_) => return HttpResponse::Ok().json(json!({"volatility": "N/A", "churn_rate": 0})),
    };

    if data.len() < 2 {
        return HttpResponse::Ok().json(json!({"volatility": "N/A", "churn_rate": 0}));
    }

    let changes: Vec<i32> = (0..data.len() - 1)
        .map(|i| (data[i + 1].provider_count - data[i].provider_count).abs())
        .collect();

    let avg_change = if changes.is_empty() {
        0.0
    } else {
        changes.iter().sum::<i32>() as f64 / changes.len() as f64
    };

    let volatility = if avg_change > 100.0 {
        "high"
    } else if avg_change > 50.0 {
        "medium"
    } else {
        "low"
    };

    HttpResponse::Ok().json(json!({
        "volatility": volatility,
        "churn_rate": (avg_change * 10.0).round() / 10.0
    }))
}

pub async fn api_country(state: web::Data<AppState>, path: web::Path<String>) -> HttpResponse {
    let pool = &state.pool;
    let code = path.into_inner();

    match db::get_country_history(pool, &code, 720).await {
        Ok(data) => {
            let response: Vec<_> = data
                .iter()
                .map(|d| json!({"timestamp": d.timestamp, "count": d.provider_count}))
                .collect();
            HttpResponse::Ok().json(response)
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

pub async fn api_growth_projection(state: web::Data<AppState>) -> HttpResponse {
    let pool = &state.pool;
    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let current = match db::get_total_at_timestamp(pool, &latest).await {
        Ok(Some(t)) => t,
        Ok(None) => 0,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let day_ago = format_time_offset(&latest, -1440);
    let past = db::get_total_at_timestamp(pool, &day_ago).await.unwrap_or(None).unwrap_or(current);

    let daily_growth = current - past;
    let growth_rate = if past > 0 {
        ((daily_growth as f64) / (past as f64)) * 100.0
    } else {
        0.0
    };

    let capped_growth = (daily_growth).max(-1000).min(1000);
    let projected_30d = ((current as i32) + (capped_growth * 30)) as i32;
    let projected_90d = ((current as i32) + (capped_growth * 90)) as i32;

    HttpResponse::Ok().json(json!({
        "current": current,
        "daily_growth": daily_growth,
        "growth_rate": growth_rate.max(-100.0).min(100.0),
        "projected_30d": projected_30d.max(0),
        "projected_90d": projected_90d.max(0)
    }))
}

// Helper function - offset is in minutes
fn format_time_offset(timestamp: &str, offset_minutes: i32) -> String {
    // Try RFC3339 first, then fall back to naive datetime format
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(timestamp) {
        let offset_dt = dt + Duration::minutes(offset_minutes as i64);
        offset_dt.format("%Y-%m-%d %H:%M:%S").to_string()
    } else if let Ok(ndt) = chrono::NaiveDateTime::parse_from_str(timestamp, "%Y-%m-%d %H:%M:%S") {
        let offset_ndt = ndt + Duration::minutes(offset_minutes as i64);
        offset_ndt.format("%Y-%m-%d %H:%M:%S").to_string()
    } else {
        timestamp.to_string()
    }
}
