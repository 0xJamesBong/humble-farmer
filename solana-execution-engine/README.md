# execution-engine (Rust)

Rust binary that reads `contracts/strategy_spec.json` and `contracts/assets_map.json`, computes rebalance deltas, runs risk checks, and (when enabled) executes swaps on **Solana via Jupiter**. Intended for **future on-chain** execution.

**Current execution** is on Binance via [binance-execution-engine](../binance-execution-engine/) (Python). This engine is kept in the repo for when you re-enable on-chain (Solana/Jupiter); no code removal.

## Usage (when using on-chain)

- `--strategy-spec`, `--assets-map`, `--rpc-url`, `--wallet`
- Default: `--simulate` (print planned trades, no send)
- `--execute`: sign and send Jupiter swap transactions
