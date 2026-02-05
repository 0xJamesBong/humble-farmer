# Strategy Engine — Python commands

How to run the strategy-engine from the repo. See [ARCHITECTURE.md](ARCHITECTURE.md) for design and modules.

---

## Run from repo root

Set `PYTHONPATH=strategy-engine` so the `strategy_engine` package resolves. All examples assume you are in the **repo root** (parent of `strategy-engine/`).

```bash
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py [OPTIONS]
```

---

## CLI: `run_backtest.py`

**Description:** Run a bar-by-bar backtest with CCXT 4H data, then write `contracts/strategy_spec.json` (v2 orders). Optionally write ledger and/or report JSON.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--exchange` | str | `binance` | CCXT exchange id. |
| `--symbols` | str | `BTC/USDT` | Comma-separated symbols (used when **no** `--strategy`). |
| `--since` | int | (none) | Start time in milliseconds (optional). |
| `--limit` | int | `2000` | Number of 4H bars per symbol. |
| `--fee-bps` | float | `0.0` | Fee in basis points per fill. |
| `--output` | path | `contracts/strategy_spec.json` | Output path for strategy_spec.json. |
| `--ledger` | path? | (none) | Write ledger: use `--ledger PATH` to write JSON; use `--ledger` (no path) to print summary only. |
| `--report` | path | (none) | Write backtest report JSON to PATH. |
| `--starting-balance` | float | `10000.0` | Starting balance used for report metrics. |
| `--strategy` | path | (none) | Path to strategy YAML/JSON; uses config symbol and detector+risk+sizing (strategy-as-data). |
| `--plot` | path? | (none) | PnL/equity graph: `--plot` saves to `out/pnl.png` and opens it; `--plot PATH` saves to PATH only. |

**Behaviour:**

- Without `--strategy`: uses `--symbols` and the default hardcoded detector (`detect_setup` → full `TradeSetup`).
- With `--strategy path/to/strategy.yaml`: loads that config, uses its `symbol` and builds `TradeSetup` via `detect_event` + risk + sizing.

---

## Example commands

All examples use **2000 candles** (4H bars), **$10,000 USD starting capital**, and **BTC/USDT** unless a strategy file sets the symbol.

**Default (hardcoded detector, BTC):**

```bash
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py \
  --exchange binance \
  --symbols "BTC/USDT" \
  --limit 2000 \
  --starting-balance 10000
```

**Strategy-as-data (one YAML strategy; symbol from config):**

```bash
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py \
  --exchange binance \
  --strategy strategy-engine/strategies/ema_inflection_v1.yaml \
  --limit 2000 \
  --starting-balance 10000
```

**With ledger summary (no file):**

```bash
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py \
  --exchange binance \
  --symbols "BTC/USDT" \
  --limit 2000 \
  --starting-balance 10000 \
  --ledger
```

**With ledger JSON, report JSON, and PnL graph (display):**

```bash
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py \
  --exchange binance \
  --strategy strategy-engine/strategies/ema_inflection_v1.yaml \
  --limit 2000 \
  --ledger out/ledger.json \
  --report out/report.json \
  --starting-balance 10000 \
  --plot
```

**Save PnL graph to file:**

```bash
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py \
  --exchange binance \
  --symbols "BTC/USDT" \
  --limit 2000 \
  --starting-balance 10000 \
  --plot out/pnl.png
```

**Custom output path and fees (BTC):**

```bash
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py \
  --exchange binance \
  --symbols "BTC/USDT" \
  --limit 2000 \
  --starting-balance 10000 \
  --fee-bps 10 \
  --output contracts/my_spec.json
```

---

## Outputs

| Output | When | Location / behaviour |
|--------|------|----------------------|
| **strategy_spec.json (v2)** | Always | `contracts/strategy_spec.json` (or `--output`). Contains `orders` with entry, stop_loss, take_profit, size. |
| **Ledger summary** | `--ledger` (no path) | Printed to stdout: fill count, trade count, `pnl_net`. |
| **Ledger JSON** | `--ledger PATH` | Written to PATH: fills and completed_trades. |
| **Report JSON** | `--report PATH` | Written to PATH: performance metrics and equity curve from ledger. |

---

## Dependencies

Install in the repo (e.g. with uv or pip):

```bash
# from repo root, install strategy-engine in editable mode
pip install -e strategy-engine
# or
uv pip install -e strategy-engine
```

Required: `pandas`, `numpy`, `ccxt`, `pyyaml`, `pydantic`, `matplotlib` (see `strategy-engine/pyproject.toml`).
