//! Jupiter: quote -> build swap tx -> simulate or send. CapitalSource::SpotOnly for future Kamino seam.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use solana_client::rpc_client::RpcClient;
use solana_sdk::commitment_config::CommitmentConfig;
use solana_sdk::signature::Signer;
use solana_sdk::transaction::Transaction;

use crate::config::AssetsMap;
use crate::risk::PlannedTrade;

#[derive(Debug)]
pub enum CapitalSource {
    SpotOnly,
    // Lending { ... }  // commented, not implemented
}

/// Jupiter quote response (minimal fields for MVP).
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JupiterQuote {
    pub input_mint: String,
    pub output_mint: String,
    pub in_amount: String,
    pub out_amount: String,
    // We only need in/out for simulation display; full swap uses swap API.
}

const JUPITER_QUOTE_URL: &str = "https://quote-api.jup.ag/v6/quote";
const JUPITER_SWAP_URL: &str = "https://quote-api.jup.ag/v6/swap";

/// Fetch a quote from Jupiter for one swap. MVP: just fetch and return; no tx build yet.
pub async fn fetch_quote(
    input_mint: &str,
    output_mint: &str,
    amount_lamports: u64,
    slippage_bps: u16,
) -> Result<JupiterQuote> {
    let client = reqwest::Client::new();
    let url = format!(
        "{}?inputMint={}&outputMint={}&amount={}&slippageBps={}",
        JUPITER_QUOTE_URL,
        input_mint,
        output_mint,
        amount_lamports,
        slippage_bps
    );
    let resp = client
        .get(&url)
        .send()
        .await
        .context("Jupiter quote request")?;
    let status = resp.status();
    let body = resp.text().await.context("Jupiter quote body")?;
    if !status.is_success() {
        anyhow::bail!("Jupiter quote failed {}: {}", status, body);
    }
    let quote: JupiterQuote =
        serde_json::from_str(&body).with_context(|| format!("parse Jupiter quote: {}", body))?;
    Ok(quote)
}

/// Simulate: for each planned trade, fetch Jupiter quote and print what would be done.
/// If quote API fails (e.g. no network), prints planned trade without quote and continues.
pub async fn simulate_trades(
    assets: &AssetsMap,
    planned: &[PlannedTrade],
    slippage_bps: u16,
) -> Result<()> {
    for t in planned {
        if t.delta_raw == 0 {
            continue;
        }
        let (input_mint, output_mint, amount) = if t.delta_raw > 0 {
            let usdt = assets
                .get("USDT")
                .or_else(|| assets.get("USDC"))
                .map(|a| a.mint.as_str())
                .ok_or_else(|| anyhow::anyhow!("No USDT/USDC in assets_map for buy"))?;
            (usdt, t.mint.as_str(), t.delta_raw as u64)
        } else {
            let usdt = assets
                .get("USDT")
                .or_else(|| assets.get("USDC"))
                .map(|a| a.mint.as_str())
                .ok_or_else(|| anyhow::anyhow!("No USDT/USDC in assets_map for sell"))?;
            (t.mint.as_str(), usdt, (-t.delta_raw) as u64)
        };
        match fetch_quote(input_mint, output_mint, amount, slippage_bps).await {
            Ok(quote) => println!(
                "  Would swap {} -> {} (quote: in={} out={})",
                input_mint, output_mint, quote.in_amount, quote.out_amount
            ),
            Err(e) => println!(
                "  Would swap {} -> {} (amount={}; quote skipped: {})",
                input_mint, output_mint, amount, e
            ),
        }
    }
    Ok(())
}

/// Request body for Jupiter swap API.
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct SwapRequest {
    quote_response: serde_json::Value,
    user_public_key: String,
    wrap_and_unwrap_sol: bool,
}

/// Response from Jupiter swap API (minimal).
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SwapResponse {
    swap_transaction: String,
}

/// Build swap transaction via Jupiter API, sign with keypair, send via RPC.
/// Fails on first error (no partial execution).
pub async fn execute_trades(
    assets: &AssetsMap,
    planned: &[PlannedTrade],
    slippage_bps: u16,
    keypair: &solana_sdk::signature::Keypair,
    rpc_url: &str,
) -> Result<()> {
    let client = reqwest::Client::new();
    let rpc = RpcClient::new_with_commitment(rpc_url.to_string(), CommitmentConfig::confirmed());
    let user_pubkey = keypair.pubkey().to_string();

    for t in planned {
        if t.delta_raw == 0 {
            continue;
        }
        let (input_mint, output_mint, amount) = if t.delta_raw > 0 {
            let usdt = assets
                .get("USDT")
                .or_else(|| assets.get("USDC"))
                .map(|a| a.mint.as_str())
                .ok_or_else(|| anyhow::anyhow!("No USDT/USDC in assets_map for buy"))?;
            (usdt, t.mint.as_str(), t.delta_raw as u64)
        } else {
            let usdt = assets
                .get("USDT")
                .or_else(|| assets.get("USDC"))
                .map(|a| a.mint.as_str())
                .ok_or_else(|| anyhow::anyhow!("No USDT/USDC in assets_map for sell"))?;
            (t.mint.as_str(), usdt, (-t.delta_raw) as u64)
        };

        let quote_url = format!(
            "{}?inputMint={}&outputMint={}&amount={}&slippageBps={}",
            JUPITER_QUOTE_URL, input_mint, output_mint, amount, slippage_bps
        );
        let quote_body = client.get(&quote_url).send().await.context("Jupiter quote")?.text().await?;
        let quote_json: serde_json::Value = serde_json::from_str(&quote_body).context("parse quote")?;

        let swap_body = SwapRequest {
            quote_response: quote_json,
            user_public_key: user_pubkey.clone(),
            wrap_and_unwrap_sol: true,
        };
        let swap_resp = client
            .post(JUPITER_SWAP_URL)
            .json(&swap_body)
            .send()
            .await
            .context("Jupiter swap request")?;
        let status = swap_resp.status();
        let swap_text = swap_resp.text().await.context("Jupiter swap body")?;
        if !status.is_success() {
            anyhow::bail!("Jupiter swap failed {}: {}", status, swap_text);
        }
        let swap_result: SwapResponse = serde_json::from_str(&swap_text).context("parse swap response")?;
        let tx_bytes = base64::Engine::decode(
            &base64::engine::general_purpose::STANDARD,
            &swap_result.swap_transaction,
        )
        .context("decode swap transaction")?;
        let mut tx: Transaction = bincode::deserialize(&tx_bytes).context("deserialize transaction")?;
        tx.sign(&[keypair], tx.message.recent_blockhash);
        let sig = rpc.send_and_confirm_transaction(&tx).context("send transaction")?;
        println!("  Executed swap {} -> {}: {}", input_mint, output_mint, sig);
    }
    Ok(())
}
