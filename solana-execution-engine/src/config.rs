//! Parse strategy_spec.json and assets_map.json.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Deserialize)]
pub struct StrategySpec {
    pub version: u32,
    pub generated_at_utc: String,
    pub period_4h_end_utc: String,
    pub leverage_allowed: bool,
    pub target_weights: HashMap<String, f64>,
}

#[derive(Debug, Deserialize)]
pub struct AssetInfo {
    pub mint: String,
    pub decimals: u8,
}

pub type AssetsMap = HashMap<String, AssetInfo>;

pub fn load_strategy_spec(path: &Path) -> Result<StrategySpec> {
    let s = std::fs::read_to_string(path)
        .with_context(|| format!("read strategy_spec: {}", path.display()))?;
    serde_json::from_str(&s).with_context(|| "parse strategy_spec.json")
}

pub fn load_assets_map(path: &Path) -> Result<AssetsMap> {
    let s = std::fs::read_to_string(path)
        .with_context(|| format!("read assets_map: {}", path.display()))?;
    serde_json::from_str(&s).with_context(|| "parse assets_map.json")
}

pub fn validate_spec_against_assets(spec: &StrategySpec, assets: &AssetsMap) -> Result<()> {
    for symbol in spec.target_weights.keys() {
        if !assets.contains_key(symbol) {
            anyhow::bail!("target_weights symbol '{}' not in assets_map", symbol);
        }
    }
    Ok(())
}
