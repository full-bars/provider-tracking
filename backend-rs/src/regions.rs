use lazy_static::lazy_static;
use std::collections::HashMap;

lazy_static! {
    pub static ref REGIONS: HashMap<&'static str, &'static str> = {
        let mut m = HashMap::new();
        // North America
        m.insert("us", "North America");
        m.insert("ca", "North America");
        m.insert("mx", "North America");

        // Europe
        m.insert("gb", "Europe");
        m.insert("de", "Europe");
        m.insert("fr", "Europe");
        m.insert("es", "Europe");
        m.insert("fi", "Europe");
        m.insert("nl", "Europe");
        m.insert("se", "Europe");
        m.insert("no", "Europe");
        m.insert("dk", "Europe");
        m.insert("it", "Europe");
        m.insert("pl", "Europe");
        m.insert("cz", "Europe");
        m.insert("at", "Europe");
        m.insert("ch", "Europe");
        m.insert("be", "Europe");
        m.insert("ie", "Europe");
        m.insert("pt", "Europe");
        m.insert("ru", "Europe");
        m.insert("ua", "Europe");
        m.insert("ro", "Europe");
        m.insert("bg", "Europe");
        m.insert("hu", "Europe");
        m.insert("lt", "Europe");
        m.insert("lv", "Europe");
        m.insert("sk", "Europe");
        m.insert("hr", "Europe");
        m.insert("rs", "Europe");
        m.insert("md", "Europe");
        m.insert("by", "Europe");
        m.insert("is", "Europe");
        m.insert("lu", "Europe");
        m.insert("mt", "Europe");
        m.insert("si", "Europe");
        m.insert("cy", "Europe");
        m.insert("gr", "Europe");
        m.insert("mk", "Europe");
        m.insert("al", "Europe");
        m.insert("ba", "Europe");
        m.insert("am", "Europe");
        m.insert("ge", "Europe");
        m.insert("kz", "Europe");
        m.insert("az", "Europe");
        m.insert("xk", "Europe");
        m.insert("ee", "Europe");
        m.insert("li", "Europe");
        m.insert("mc", "Europe");
        m.insert("ad", "Europe");
        m.insert("tr", "Europe");

        // Asia-Pacific
        m.insert("vn", "Asia-Pacific");
        m.insert("sg", "Asia-Pacific");
        m.insert("hk", "Asia-Pacific");
        m.insert("kr", "Asia-Pacific");
        m.insert("in", "Asia-Pacific");
        m.insert("jp", "Asia-Pacific");
        m.insert("th", "Asia-Pacific");
        m.insert("my", "Asia-Pacific");
        m.insert("id", "Asia-Pacific");
        m.insert("ph", "Asia-Pacific");
        m.insert("cn", "Asia-Pacific");
        m.insert("tw", "Asia-Pacific");
        m.insert("bd", "Asia-Pacific");
        m.insert("kh", "Asia-Pacific");
        m.insert("mn", "Asia-Pacific");
        m.insert("mm", "Asia-Pacific");
        m.insert("la", "Asia-Pacific");
        m.insert("nz", "Asia-Pacific");
        m.insert("au", "Asia-Pacific");
        m.insert("lk", "Asia-Pacific");
        m.insert("np", "Asia-Pacific");
        m.insert("uz", "Asia-Pacific");
        m.insert("tj", "Asia-Pacific");
        m.insert("kg", "Asia-Pacific");
        m.insert("pk", "Asia-Pacific");

        // Middle East
        m.insert("ir", "Middle East");
        m.insert("ae", "Middle East");
        m.insert("sa", "Middle East");
        m.insert("il", "Middle East");
        m.insert("jo", "Middle East");
        m.insert("qa", "Middle East");
        m.insert("kw", "Middle East");
        m.insert("iq", "Middle East");
        m.insert("sy", "Middle East");
        m.insert("lb", "Middle East");
        m.insert("ps", "Middle East");
        m.insert("bh", "Middle East");
        m.insert("om", "Middle East");

        // South America
        m.insert("br", "South America");
        m.insert("ar", "South America");
        m.insert("co", "South America");
        m.insert("cl", "South America");
        m.insert("pe", "South America");
        m.insert("uy", "South America");
        m.insert("py", "South America");
        m.insert("ec", "South America");
        m.insert("bo", "South America");
        m.insert("ve", "South America");
        m.insert("cr", "South America");
        m.insert("pa", "South America");
        m.insert("hn", "South America");
        m.insert("gt", "South America");
        m.insert("jm", "South America");
        m.insert("do", "South America");
        m.insert("pr", "South America");
        m.insert("ky", "South America");
        m.insert("bs", "South America");
        m.insert("vi", "South America");
        m.insert("bq", "South America");
        m.insert("tt", "South America");
        m.insert("gd", "South America");

        // Africa
        m.insert("ng", "Africa");
        m.insert("ma", "Africa");
        m.insert("ke", "Africa");
        m.insert("za", "Africa");
        m.insert("sn", "Africa");
        m.insert("tz", "Africa");
        m.insert("ug", "Africa");
        m.insert("mz", "Africa");
        m.insert("gh", "Africa");
        m.insert("cd", "Africa");
        m.insert("et", "Africa");
        m.insert("ga", "Africa");
        m.insert("ci", "Africa");
        m.insert("tn", "Africa");
        m.insert("eg", "Africa");
        m.insert("ly", "Africa");
        m.insert("dz", "Africa");
        m.insert("mu", "Africa");
        m.insert("bw", "Africa");

        m
    };
}

pub fn get_region(country_code: &str) -> &'static str {
    REGIONS.get(country_code).copied().unwrap_or("Other")
}
