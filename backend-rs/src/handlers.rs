use actix_web::{web, HttpResponse, HttpRequest};
use serde_json::json;
use chrono::{Duration};
use std::collections::HashMap;

use crate::{AppState, models::*, db, regions};

pub async fn api_summary(
    state: web::Data<AppState>,
) -> HttpResponse {
    let pool = &state.pool;

    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(e) => {
            log::error!("Failed to get latest timestamp: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    let current_total = match db::get_total_at_timestamp(pool, &latest).await {
        Ok(total) => total,
        Err(e) => {
            log::error!("Failed to get current total: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    // Hour-over-hour delta
    let hour_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::hours(1)).to_rfc3339()))
        .unwrap_or_default();

    let hour_ago_total = db::get_total_at_timestamp(pool, &hour_ago).await
        .unwrap_or(current_total);
    let hour_delta = current_total - hour_ago_total;

    // Day-over-day delta
    let day_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::days(1)).to_rfc3339()))
        .unwrap_or_default();

    let day_ago_total = db::get_total_at_timestamp(pool, &day_ago).await
        .unwrap_or(current_total);
    let day_delta = current_total - day_ago_total;

    // Top 10
    let top_10 = match db::get_top_countries(pool, &latest, 10).await {
        Ok(countries) => countries,
        Err(e) => {
            log::error!("Failed to get top 10: {}", e);
            vec![]
        }
    };

    let response = SummaryResponse {
        timestamp: latest,
        total: current_total,
        hour_delta,
        day_delta,
        top_10,
    };

    HttpResponse::Ok().json(response)
}

pub async fn api_network_total(
    state: web::Data<AppState>,
) -> HttpResponse {
    let pool = &state.pool;

    match db::get_network_totals(pool, 168).await {
        Ok(data) => HttpResponse::Ok().json(data),
        Err(e) => {
            log::error!("Failed to get network total: {}", e);
            HttpResponse::InternalServerError().finish()
        }
    }
}

pub async fn api_regions(
    state: web::Data<AppState>,
) -> HttpResponse {
    let pool = &state.pool;

    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(e) => {
            log::error!("Failed to get latest timestamp: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    let day_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::days(1)).to_rfc3339()))
        .unwrap_or_default();

    // Get current regional totals
    let current_countries = match db::get_countries_at_timestamp(pool, &latest).await {
        Ok(countries) => countries,
        Err(e) => {
            log::error!("Failed to get countries: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    let mut region_totals: HashMap<&'static str, (i32, i32)> = HashMap::new();

    for cc in current_countries.iter() {
        let region = regions::get_region(&cc.country_code);
        let entry = region_totals.entry(region).or_insert((0, 0));
        entry.0 += cc.provider_count;

        // Get past count for delta
        if let Ok(Some(past_count)) = db::get_country_at_time(pool, &cc.country_code, &day_ago).await {
            entry.1 -= (cc.provider_count - past_count);
        }
    }

    let mut regions: Vec<Region> = region_totals
        .into_iter()
        .map(|(region, (total, delta))| Region {
            region: region.to_string(),
            total,
            delta_24h: delta,
        })
        .collect();

    regions.sort_by(|a, b| b.total.cmp(&a.total));

    HttpResponse::Ok().json(regions)
}

pub async fn api_at_risk(
    state: web::Data<AppState>,
) -> HttpResponse {
    let pool = &state.pool;

    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(e) => {
            log::error!("Failed to get latest timestamp: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    let day_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::days(1)).to_rfc3339()))
        .unwrap_or_default();

    let current_countries = match db::get_countries_at_timestamp(pool, &latest).await {
        Ok(countries) => countries,
        Err(e) => {
            log::error!("Failed to get countries: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    let mut disappeared = Vec::new();
    let mut near_zero = Vec::new();

    for cc in current_countries.iter() {
        if cc.provider_count == 0 {
            // Check if it had providers 24h ago
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
            // Check if declining
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

    let response = AtRisk {
        disappeared,
        near_zero,
    };

    HttpResponse::Ok().json(response)
}

pub async fn api_anomalies(
    state: web::Data<AppState>,
    query: web::Query<HashMap<String, String>>,
) -> HttpResponse {
    let pool = &state.pool;

    let threshold_str = query.get("threshold").map(|s| s.as_str()).unwrap_or("15");
    let threshold_pct: f64 = threshold_str.parse().unwrap_or(15.0);
    let threshold = threshold_pct / 100.0;

    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(e) => {
            log::error!("Failed to get latest timestamp: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    let hour_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::hours(1)).to_rfc3339()))
        .unwrap_or_default();

    match db::get_anomalies(pool, &latest, &hour_ago, threshold).await {
        Ok((gains, losses)) => {
            HttpResponse::Ok().json(AnomaliesResponse { gains, losses })
        }
        Err(e) => {
            log::error!("Failed to get anomalies: {}", e);
            HttpResponse::InternalServerError().finish()
        }
    }
}

pub async fn api_movers(
    state: web::Data<AppState>,
) -> HttpResponse {
    let pool = &state.pool;

    let latest = match db::get_latest_timestamp(pool).await {
        Ok(ts) => ts,
        Err(e) => {
            log::error!("Failed to get latest timestamp: {}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    let hour_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::hours(1)).to_rfc3339()))
        .unwrap_or_default();
    let day_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::days(1)).to_rfc3339()))
        .unwrap_or_default();
    let week_ago = chrono::DateTime::parse_from_rfc3339(&latest)
        .ok()
        .and_then(|dt| Some((dt - Duration::days(7)).to_rfc3339()))
        .unwrap_or_default();

    let (hour_gainers, hour_losers) = db::get_movers(pool, &hour_ago, &latest).await
        .unwrap_or((vec![], vec![]));
    let (day_gainers, day_losers) = db::get_movers(pool, &day_ago, &latest).await
        .unwrap_or((vec![], vec![]));
    let (week_gainers, week_losers) = db::get_movers(pool, &week_ago, &latest).await
        .unwrap_or((vec![], vec![]));

    let response = MoversResponse {
        one_hour: WindowMovers {
            gainers: hour_gainers,
            losers: hour_losers,
        },
        day: WindowMovers {
            gainers: day_gainers,
            losers: day_losers,
        },
        week: WindowMovers {
            gainers: week_gainers,
            losers: week_losers,
        },
    };

    HttpResponse::Ok().json(response)
}

pub async fn api_movers_detailed(
    state: web::Data<AppState>,
) -> HttpResponse {
    HttpResponse::Ok().json(json!({"status": "not implemented"}))
}

pub async fn api_country_stats(
    state: web::Data<AppState>,
) -> HttpResponse {
    HttpResponse::Ok().json(json!({"status": "not implemented"}))
}

pub async fn api_country(
    state: web::Data<AppState>,
    query: web::Query<HashMap<String, String>>,
) -> HttpResponse {
    HttpResponse::Ok().json(json!({"status": "not implemented"}))
}
