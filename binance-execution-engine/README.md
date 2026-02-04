# binance-execution-engine

Python package that reads `contracts/strategy_spec.json` and executes the target portfolio on **Binance spot** via CCXT (market orders). Part of the humble-farmer monorepo; strategy is produced by [strategy-engine](../strategy-engine/), this engine only executes.

## Contract

Reads **strategy_spec.json** from repo root `contracts/` (or path given by `--strategy-spec`). The spec contains `target_weights` (e.g. USDT, SOL, WBTC, WETH). This engine maps them to Binance pairs (SOL/USDT, BTC/USDT, ETH/USDT) and rebalances.

## API keys

Set environment variables (do not commit):

- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`

Optional: put them in a `.env` file at repo root (gitignored). This package does not load `.env` by default; use `python-dotenv` in your own wrapper if needed.

## Usage

**Dry-run (default)** — print orders only, no trades:

```bash
# From repo root
PYTHONPATH=binance-execution-engine python binance-execution-engine/scripts/run_execute.py

# Or from inside binance-execution-engine
cd binance-execution-engine && PYTHONPATH=. python scripts/run_execute.py
```

**Live execution** — place market orders on Binance:

```bash
PYTHONPATH=binance-execution-engine python binance-execution-engine/scripts/run_execute.py --execute
```

## Options

- `--strategy-spec PATH` — path to strategy_spec.json (default: `../contracts/strategy_spec.json` when run from package, or repo `contracts/strategy_spec.json` when run from root)
- `--dry-run` — only print orders (default)
- `--execute` — place live market orders
- `--exchange` — CCXT exchange id (default: binance)

## Flow

1. Load strategy_spec.json and get target_weights.
2. Fetch Binance spot balances and prices (CCXT).
3. Compute rebalance orders (target vs current weights).
4. Dry-run: print orders; execute: place market buy/sell orders.
