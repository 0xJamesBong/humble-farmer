# binance-execution-engine

Python package that reads `contracts/strategy_spec.json` and executes on **Binance spot** via CCXT (market orders). Part of the humble-farmer monorepo; strategy is produced by [strategy-engine](../strategy-engine/), this engine only executes.

## Contract

Reads **strategy_spec.json** from repo root `contracts/` (or path given by `--strategy-spec`). Supports two spec versions:

- **v1**: `target_weights` (e.g. USDT, SOL, WBTC, WETH). Engine maps them to Binance pairs and rebalances portfolio to target weights.
- **v2**: `orders` array with discrete trades: `asset`, `side`, `entry`, `stop_loss`, `take_profit`, `size`. Engine places entry market orders for each order; SL/TP are in the spec for reference (execution is entry-only unless extended).

## API keys

Set `BINANCE_API_KEY` and `BINANCE_API_SECRET`. Either:

- **Environment**: `export BINANCE_API_KEY=...` and `export BINANCE_API_SECRET=...`
- **Repo root .env**: Copy [.env.example](../.env.example) to `.env` at the repo root and fill in your keys. The script loads `repo_root/.env` automatically via python-dotenv. Do not commit `.env`.

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

- **v1**: Load strategy_spec → target_weights → fetch balances/prices → compute rebalance orders → dry-run or place market orders.
- **v2**: Load strategy_spec → orders → map asset/side/size to pairs → dry-run or place market entry orders (one per order in the list).
