//! Fetch wallet token balances via RPC.

use anyhow::{Context, Result};
use solana_client::rpc_client::RpcClient;
use solana_client::rpc_request::TokenAccountsFilter;
use solana_sdk::commitment_config::CommitmentConfig;
use solana_sdk::program_pack::Pack;
use solana_sdk::pubkey::Pubkey;
use spl_token::state::Account as SplAccount;
use std::collections::HashMap;

/// Balance in raw units (lamports for SOL, token units for SPL).
#[derive(Debug, Clone, Default)]
pub struct Balances {
    pub sol_lamports: u64,
    pub tokens: HashMap<String, u64>, // mint (base58) -> raw amount
}

pub fn fetch_balances(
    rpc_url: &str,
    wallet_pubkey: &Pubkey,
    _assets_map: &crate::config::AssetsMap,
) -> Result<Balances> {
    let client = RpcClient::new_with_commitment(
        rpc_url.to_string(),
        CommitmentConfig::confirmed(),
    );

    let sol_balance = client
        .get_balance(wallet_pubkey)
        .context("get SOL balance")?;

    let token_program_id = spl_token::id();
    let accounts = client
        .get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountsFilter::ProgramId(token_program_id),
        )
        .context("get_token_accounts_by_owner")?;

    let mut tokens: HashMap<String, u64> = HashMap::new();
    for keyed in accounts {
        let data = keyed.account.data;
        let decoded = match data {
            solana_account_decoder::UiAccountData::Binary(s, _) => {
                base64::Engine::decode(
                    &base64::engine::general_purpose::STANDARD,
                    s,
                )
                .context("decode token account base64")?
            }
            _ => continue,
        };
        if let Ok(spl_account) = SplAccount::unpack(&decoded) {
            tokens.insert(
                spl_account.mint.to_string(),
                spl_account.amount,
            );
        }
    }

    Ok(Balances {
        sol_lamports: sol_balance,
        tokens,
    })
}
