use serde::{Deserialize, Serialize};
use std::time::Instant;

#[derive(Clone)]
pub struct CachedResponse<T: Clone> {
    pub data: T,
    pub at: Instant,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct ProviderCount {
    pub timestamp: String,
    pub country_code: String,
    pub country_name: String,
    pub provider_count: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AthAtl {
    pub value: i32,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SummaryResponse {
    pub timestamp: String,
    pub total: i32,
    pub hour_delta: i32,
    pub day_delta: i32,
    pub week_delta: i32,
    pub two_week_delta: i32,
    pub top_10: Vec<CountryCount>,
    pub hour_range: (i32, i32),
    pub day_range: (i32, i32),
    pub week_range: (i32, i32),
    pub two_week_range: (i32, i32),
    pub month_range: (i32, i32),
    pub ath: AthAtl,
    pub atl: AthAtl,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct CountryCount {
    pub country_code: String,
    pub country_name: String,
    pub provider_count: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct NetworkTotal {
    pub timestamp: String,
    pub total: i32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ma: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Region {
    pub region: String,
    pub total: i32,
    pub delta_24h: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AtRisk {
    pub disappeared: Vec<CountryCount>,
    pub near_zero: Vec<CountryCount>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Anomaly {
    pub country_code: String,
    pub country_name: String,
    pub provider_count: i32,
    pub delta: i32,
    pub percent_change: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomaliesResponse {
    pub gains: Vec<Anomaly>,
    pub losses: Vec<Anomaly>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoversResponse {
    #[serde(rename = "1h")]
    pub one_hour: WindowMovers,
    #[serde(rename = "24h")]
    pub day: WindowMovers,
    #[serde(rename = "7d")]
    pub week: WindowMovers,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowMovers {
    pub gainers: Vec<Mover>,
    pub losers: Vec<Mover>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Mover {
    pub country_code: String,
    pub country_name: String,
    pub provider_count: i32,
    pub delta: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CountryStats {
    pub code: String,
    pub name: String,
    pub current: i32,
    pub deltas: HashMap<String, i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CountryData {
    pub timestamp: String,
    pub country_code: String,
    pub country_name: String,
    pub provider_count: i32,
}

use std::collections::HashMap;
