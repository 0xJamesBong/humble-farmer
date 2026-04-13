# Contracts (future external signals)

This directory is reserved for **machine-readable handoffs** between systems that are *not* FreqTrade—for example:

- On-chain or off-chain analytics publishing **signals, scores, or risk caps**
- A future **Rust** pipeline writing JSON consumed by a thin FreqTrade integration (webhook, file watcher, or plugin)

**FreqTrade is the system of record** for Binance connectivity, candles, backtesting, hyperoptimization, paper/live trading, and order management. Do not duplicate that here.

When you define a real signal contract, document the schema in this folder and version it (e.g. `signals_v1.json`).

## Legacy note

`strategy_spec.json` may remain as a placeholder filename only; it is **not** produced by any in-repo engine anymore.
