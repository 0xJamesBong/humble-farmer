//! Risk gate: allowlist, exposure, slippage. Single module; one entry point.

use anyhow::{anyhow, Result};

use crate::config::{AssetsMap, StrategySpec};
use crate::state::Balances;

/// Planned trade: symbol (or mint) and delta in raw units (positive = buy, negative = sell).
#[derive(Debug, Clone)]
pub struct PlannedTrade {
    pub symbol: String,
    pub mint: String,
    pub delta_raw: i64,
}

/// Max allowed weight per asset (e.g. 0.5 = 50%).
const MAX_WEIGHT_PER_ASSET: f64 = 0.5;
/// Max allowed slippage in basis points (e.g. 100 = 1%).
const MAX_SLIPPAGE_BPS: u16 = 100;

/// Enforce allowlist: every planned trade's mint must be in assets_map.
fn check_allowlist(assets: &AssetsMap, planned: &[PlannedTrade]) -> Result<()> {
    let allowed_mints: std::collections::HashSet<&str> =
        assets.values().map(|a| a.mint.as_str()).collect();
    for t in planned {
        if !allowed_mints.contains(t.mint.as_str()) {
            return Err(anyhow!(
                "risk: mint {} ({}) not in assets_map allowlist",
                t.mint,
                t.symbol
            ));
        }
    }
    Ok(())
}

/// Enforce max per-asset exposure: no target weight above MAX_WEIGHT_PER_ASSET.
fn check_exposure(spec: &StrategySpec) -> Result<()> {
    for (symbol, w) in &spec.target_weights {
        if *w > MAX_WEIGHT_PER_ASSET {
            return Err(anyhow!(
                "risk: target weight for {} ({}) exceeds max {}",
                symbol,
                w,
                MAX_WEIGHT_PER_ASSET
            ));
        }
    }
    Ok(())
}

/// Enforce max slippage: slippage_bps must not exceed MAX_SLIPPAGE_BPS.
fn check_slippage(slippage_bps: u16) -> Result<()> {
    if slippage_bps > MAX_SLIPPAGE_BPS {
        return Err(anyhow!(
            "risk: slippage {} bps exceeds max {} bps",
            slippage_bps,
            MAX_SLIPPAGE_BPS
        ));
    }
    Ok(())
}

/// Risk gate: allowlist, max exposure, max slippage. Fails on first violation.
pub fn gate(
    spec: &StrategySpec,
    assets: &AssetsMap,
    _balances: &Balances,
    planned: &[PlannedTrade],
    slippage_bps: u16,
) -> Result<()> {
    check_allowlist(assets, planned)?;
    check_exposure(spec)?;
    check_slippage(slippage_bps)?;
    Ok(())
}
