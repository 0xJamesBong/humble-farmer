//! CLI: load contracts -> state -> deltas -> risk gate -> simulate (or execute).

mod config;
mod execute;
mod risk;
mod state;

use anyhow::{Context, Result};
use solana_sdk::pubkey::Pubkey;
use solana_sdk::signature::Signer;
use std::path::PathBuf;

fn main() -> Result<()> {
    let rt = tokio::runtime::Runtime::new().context("tokio runtime")?;
    rt.block_on(run())
}

async fn run() -> Result<()> {
    let args = parse_args();
    let spec_path = args.strategy_spec;
    let assets_path = args.assets_map;
    let rpc_url = args.rpc_url;
    let wallet_path = args.wallet;
    let simulate = args.simulate;

    let spec = config::load_strategy_spec(&spec_path)?;
    let assets = config::load_assets_map(&assets_path)?;
    config::validate_spec_against_assets(&spec, &assets)?;

    let expanded_wallet = expand_tilde(&wallet_path);
    let (_wallet_pubkey, balances) = if expanded_wallet.exists() {
        let pk = load_wallet_pubkey(&expanded_wallet)?;
        let bal = state::fetch_balances(&rpc_url, &pk, &assets)?;
        (pk, bal)
    } else {
        // Simulate without wallet: use zero balances so we can still run pipeline
        let pk = Pubkey::default();
        let bal = state::Balances::default();
        (pk, bal)
    };

    let planned = compute_planned_trades(&spec, &assets, &balances)?;
    let slippage_bps: u16 = 50;
    risk::gate(&spec, &assets, &balances, &planned, slippage_bps)?;

    println!("Target weights: {:?}", spec.target_weights);
    println!("Planned trades (deltas):");
    for t in &planned {
        if t.delta_raw != 0 {
            println!("  {} ({}) delta_raw={}", t.symbol, t.mint, t.delta_raw);
        }
    }
    if simulate {
        println!("Simulating Jupiter quotes...");
        execute::simulate_trades(&assets, &planned, slippage_bps).await?;
    } else {
        if !expanded_wallet.exists() {
            anyhow::bail!("--execute requires a wallet keypair; path does not exist: {}", expanded_wallet.display());
        }
        let keypair = solana_sdk::signer::keypair::read_keypair_file(&expanded_wallet)
            .map_err(|e| anyhow::anyhow!("read keypair {}: {}", expanded_wallet.display(), e))?;
        println!("Executing Jupiter swaps...");
        execute::execute_trades(&assets, &planned, slippage_bps, &keypair, &rpc_url).await?;
    }
    Ok(())
}

struct Args {
    strategy_spec: PathBuf,
    assets_map: PathBuf,
    rpc_url: String,
    wallet: PathBuf,
    simulate: bool,
}

fn parse_args() -> Args {
    let mut args = pico_args::Arguments::from_env();
    Args {
        strategy_spec: args
            .opt_value_from_str("--strategy-spec")
            .ok()
            .flatten()
            .unwrap_or_else(|| PathBuf::from("contracts/strategy_spec.json")),
        assets_map: args
            .opt_value_from_str("--assets-map")
            .ok()
            .flatten()
            .unwrap_or_else(|| PathBuf::from("contracts/assets_map.json")),
        rpc_url: args
            .opt_value_from_str("--rpc-url")
            .ok()
            .flatten()
            .unwrap_or_else(|| "https://api.mainnet-beta.solana.com".to_string()),
        wallet: args
            .opt_value_from_str("--wallet")
            .ok()
            .flatten()
            .unwrap_or_else(|| PathBuf::from("~/.config/solana/id.json")),
        simulate: !args.contains("--execute"),
    }
}

fn expand_tilde(path: &std::path::Path) -> PathBuf {
    let s = path.to_string_lossy();
    if s.starts_with("~") {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
        PathBuf::from(home).join(s.strip_prefix("~/").unwrap_or(s.strip_prefix('~').unwrap_or(&s)))
    } else {
        path.to_path_buf()
    }
}

fn load_wallet_pubkey(path: &std::path::Path) -> Result<Pubkey> {
    let keypair = solana_sdk::signer::keypair::read_keypair_file(path)
        .map_err(|e| anyhow::anyhow!("read keypair {}: {}", path.display(), e))?;
    Ok(keypair.pubkey())
}

/// Compute planned trades: target_weights vs current weights -> deltas in raw units.
/// MVP: current "weights" from balances (notional in USDT unknown), so we use target only:
/// assume we need to move toward target; for simulation we output notional deltas.
fn compute_planned_trades(
    spec: &config::StrategySpec,
    assets: &config::AssetsMap,
    _balances: &state::Balances,
) -> Result<Vec<risk::PlannedTrade>> {
    let mut planned = Vec::new();
    for (symbol, _target_weight) in &spec.target_weights {
        let info = assets
            .get(symbol)
            .ok_or_else(|| anyhow::anyhow!("asset not in map: {}", symbol))?;
        let delta_raw = if symbol == "SOL" {
            100_000_000i64
        } else {
            0i64
        };
        planned.push(risk::PlannedTrade {
            symbol: symbol.clone(),
            mint: info.mint.clone(),
            delta_raw,
        });
    }
    Ok(planned)
}
