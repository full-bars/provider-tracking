use actix_web::{web, App, HttpServer, HttpResponse, middleware};
use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use anyhow::Result;

mod models;
mod handlers;
mod db;
mod regions;

use handlers::*;

#[derive(Clone)]
pub struct AppState {
    pool: SqlitePool,
}

#[actix_web::main]
async fn main() -> Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    let database_url = match std::env::var("DATABASE_URL") {
        Ok(url) => url,
        Err(_) => {
            format!(
                "sqlite://{}",
                std::path::PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/home/user".to_string()))
                    .join("provider_tracking/providers.db")
                    .display()
            )
        }
    };

    log::info!("Connecting to database: {}", database_url);

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await?;

    log::info!("Database connected successfully");

    let state = AppState { pool };

    log::info!("Starting server on http://0.0.0.0:5001");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .wrap(middleware::Logger::default())
            .service(
                web::scope("")
                    .route("/", web::get().to(dashboard))
                    .service(
                        web::scope("/api")
                            .route("/summary", web::get().to(api_summary))
                            .route("/network_total", web::get().to(api_network_total))
                            .route("/live_total", web::get().to(api_live_total))
                            .route("/regions", web::get().to(api_regions))
                            .route("/at-risk", web::get().to(api_at_risk))
                            .route("/anomalies", web::get().to(api_anomalies))
                            .route("/movers", web::get().to(api_movers))
                            .route("/movers-detailed", web::get().to(api_movers_detailed))
                            .route("/top-countries", web::get().to(api_top_countries))
                            .route("/growth-projection", web::get().to(api_growth_projection))
                            .route("/country-stats/{code}", web::get().to(api_country_stats))
                            .route("/country/{code}", web::get().to(api_country))
                            .route("/churn/{code}", web::get().to(api_churn))
                            .route("/comparison/{code1}/{code2}", web::get().to(api_comparison))
                    )
            )
    })
    .bind("0.0.0.0:5001")?
    .run()
    .await?;

    Ok(())
}

async fn dashboard() -> HttpResponse {
    let html = include_str!("../index.html");
    HttpResponse::Ok()
        .content_type("text/html; charset=utf-8")
        .body(html)
}
