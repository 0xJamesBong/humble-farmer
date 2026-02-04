# Contract boundary

[strategy-engine](../strategy-engine/) (Python) writes; execution engines read. These files are the only handshake.

**Consumers of strategy_spec.json:**

1. **binance-execution-engine** (Python) — current: reads target_weights, executes rebalance on Binance spot via CCXT.
2. **execution-engine** (Rust) — deferred: for future on-chain (Solana/Jupiter); reads target_weights and resolves symbols via assets_map.json.

## strategy_spec.json

Produced by the strategy engine. Schema:

- **version** (int): Contract version; must be 1 for MVP.
- **generated_at_utc** (string): ISO 8601 UTC time when the spec was generated.
- **period_4h_end_utc** (string): ISO 8601 UTC time of the 4H bar this spec applies to.
- **leverage_allowed** (bool): Must be false for MVP.
- **target_weights** (object): Symbol → weight (0–1). Weights should sum to 1.0. Symbols (e.g. USDT, SOL, WBTC, WETH). Binance engine maps these to pairs (SOL/USDT, BTC/USDT, ETH/USDT); Rust engine (when used) resolves to Solana mints via assets_map.json.

## assets_map.json

For the **Rust execution-engine** (on-chain) path only. Static map: symbol → `{ "mint": "<base58>", "decimals": <int> }`. Not used by binance-execution-engine.
