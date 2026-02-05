# Strategy Engine — Architecture

Mid-frequency trade engine: setup detection → trade state machine → orders. Same 4H cadence and JSON contract boundary; output is **orders with lifecycle** (entry, stop_loss, take_profit), not target weights. Supports **strategy-as-data** (one YAML/JSON file per strategy) and **bar-by-bar backtest** with a ledger.

---

## Pipeline

**Bar-by-bar loop (backtest):**

```
fetch_4h_candles (data.py)
    → for each bar i from warmup to end:
          df_slice = df.iloc[:i+1], bar = df.iloc[i]
          setup = detect_setup(df_slice, symbol)   # or detect_event + risk + sizing when strategy_config set
          → if state FLAT and setup: enter_trade(setup); record fills; state → OPEN
          → elif state OPEN: manage_trade(state, bar); if exit: record fills + completed trade; state → FLAT
    → return (orders_last_bar, period_end, ledger)
    → export strategy_spec (v2) with orders
```

**Rule:** A setup only **proposes** a trade. The trade state machine is the only place that decides enter/exit.

---

## Modules and Responsibilities

| Module | Responsibility |
|--------|----------------|
| **data.py** | Fetch 4H OHLCV via CCXT. Returns `symbol → DataFrame` (timestamp, open, high, low, close, volume). Research-only; no execution. |
| **types.py** | Primitives: `EventCandidate` (detector output: asset, side, entry_price, features); `TradeSetup` (proposal: asset, side, entry, stop_loss, take_profit, invalidation, confidence, size); `Order` (execution contract; serialized to strategy_spec v2). |
| **setups.py** | Setup detectors: price history → `Optional[TradeSetup]` or `Optional[EventCandidate]`. `detect_setup(df, symbol)` returns full TradeSetup (backward compat). `detect_event(df, symbol, detector_id, **params)` returns EventCandidate from **indicator registry**. Registry: `detector_id → (df, symbol, **params) → Optional[EventCandidate]`. |
| **risk.py** | `compute_stop_tp(entry_price, side, bar_or_df, risk_config)` → (stop_loss, take_profit). Config: `pct` or `atr_mult`. Pure function. |
| **sizing.py** | `compute_size(sizing_config, account_value?, volatility?)` → size. Config: `fixed` or `fixed_risk`. Pure function. |
| **trade_engine.py** | Trade state machine (FLAT / OPEN). **Fill rule (same bar):** SL checked before TP. `_exit_reason(bar, position)`, `initial_state()`, `enter_trade(setup)`, `manage_trade(state, bar)`. All enter/exit decisions live here. |
| **backtest.py** | Bar-by-bar loop: fetch candles → for each bar (warmup to end) run detect_setup or (detect_event + risk + sizing → TradeSetup), then state machine; record fills and completed trades to **ledger**. Returns `(orders_last_bar, period_end, ledger)`. |
| **ledger.py** | Ledger: fills (timestamp, asset, side, price, size, fee, exit_reason), completed_trades (entry_ts, exit_ts, asset, side, entry_price, exit_price, size, pnl_gross, fees). `to_dict()` for JSON export; `total_pnl_net`. |
| **report.py** | Backtest reporting: compute performance metrics + equity curve from ledger. Outputs overall + per-asset metrics. |
| **strategy_loader.py** | Load strategy config from YAML/JSON: `name`, `symbol`, `timeframe`, `entry` (detector_id + params), `risk`, `sizing`. `strategies_dir()` = strategy-engine/strategies/. |
| **export.py** | Write `strategy_spec.json` to repo `contracts/`. v1: target_weights (legacy). v2: `orders` array; used by backtest. |

---

## State Machine (trade_engine.py)

- **FLAT** — No open position; may accept a new setup.
- **OPEN** — Position open; track entry, stop_loss, take_profit; evaluate exit on each bar (TP/SL hit).

**Fill rule (same bar):** If both stop_loss and take_profit could be hit in one bar, **SL is checked before TP** (conservative). Backtest and live use the same rule via `_exit_reason(bar, position)`.

**Transitions:**

- FLAT + setup → `enter_trade(setup)` → OPEN, emit entry order.
- OPEN + bar → `manage_trade(state, bar)` uses `_exit_reason(bar, position)` → "sl" | "tp" | None; if exit, emit exit order, state → FLAT.
- On exit → state → FLAT.

State is in-memory per run (MVP); can be persisted later.

---

## Setup Detectors (setups.py)

- **ema_inflection_core** — Returns `Optional[EventCandidate]` (long, entry_price, features: ema_fast, ema_slow). Used by registry and by `ema_inflection` (which adds hardcoded stop/tp/size for backward compat).
- **ema_inflection** — Returns full `TradeSetup` (backward compat when no strategy config).
- **detect_setup(df, symbol)** — Returns one TradeSetup per bar or None (default path).
- **detect_event(df, symbol, detector_id, **params)** — Runs registered detector; returns EventCandidate or None (strategy-as-data path). Assembly then applies risk + sizing → TradeSetup.
- **DETECTOR_REGISTRY** — `detector_id → callable(df, symbol, **params) → Optional[EventCandidate]`. Add new strategy = one config file; add new indicator = one detector in registry.

---

## Contract: strategy_spec.json (v2)

Written to repo root `contracts/strategy_spec.json`. Consumed by execution engines (e.g. binance-execution-engine).

**v2 shape:**

```json
{
  "version": 2,
  "generated_at_utc": "ISO8601",
  "period_4h_end_utc": "ISO8601",
  "leverage_allowed": false,
  "orders": [
    {
      "asset": "SOL",
      "side": "buy",
      "entry": 98.2,
      "stop_loss": 96.7,
      "take_profit": 101.3,
      "size": 1.0
    }
  ]
}
```

Same file path as v1; `version` lets consumers branch (v1 = target_weights rebalance, v2 = discrete orders with lifecycle).

---

## Strategy-as-data

- **strategies/** — One YAML/JSON file per strategy (e.g. `strategies/ema_inflection_v1.yaml`). Schema: `name`, `symbol`, `timeframe`, `entry` (detector_id + params), `risk` (pct or atr_mult), `sizing` (fixed or fixed_risk).
- **strategy_loader.load_strategy(path)** — Load config; used by CLI `--strategy`.
- When `--strategy` is set: backtest uses `detect_event` + `risk.compute_stop_tp` + `sizing.compute_size` to build TradeSetup; symbol from config. When not set: `detect_setup` returns full TradeSetup (default symbol from `--symbols`).

**Rule of thumb:** New strategy = one strategy file; new indicator = one detector in the registry.

---

## Entrypoint

- **scripts/run_backtest.py** — CLI: `--exchange`, `--symbols`, `--since`, `--limit`, `--fee-bps`, `--output`, `--ledger` [PATH], `--strategy` PATH. Runs bar-by-bar `run_backtest()` then `export_strategy_spec_v2()`; writes `contracts/strategy_spec.json`. With `--ledger`: write ledger JSON or print summary (`--ledger` with no PATH). With `--strategy path/to/strategy.yaml`: load config, use config symbol and detector+risk+sizing.

Run from repo root:

```bash
# Default (hardcoded detector)
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py --exchange binance --symbols "SOL/USDT" --limit 100

# Strategy-as-data
PYTHONPATH=strategy-engine python strategy-engine/scripts/run_backtest.py --exchange binance --strategy strategies/ema_inflection_v1.yaml --limit 100 --ledger
```

---

## File Layout

```
strategy-engine/
├── ARCHITECTURE.md         # this file
├── pyproject.toml
├── strategies/
│   └── ema_inflection_v1.yaml   # example strategy config
├── strategy_engine/
│   ├── __init__.py
│   ├── data.py             # fetch 4H candles (CCXT)
│   ├── types.py            # EventCandidate, TradeSetup, Order
│   ├── setups.py           # detect_setup, detect_event, registry, ema_inflection
│   ├── risk.py             # compute_stop_tp (pct / atr_mult)
│   ├── sizing.py           # compute_size (fixed / fixed_risk)
│   ├── trade_engine.py     # state machine, _exit_reason, enter_trade, manage_trade
│   ├── backtest.py         # bar-by-bar loop, ledger, strategy_config → TradeSetup
│   ├── ledger.py           # Fill, CompletedTrade, Ledger
│   ├── strategy_loader.py  # load_strategy (YAML/JSON), strategies_dir
│   └── export.py           # strategy_spec v1/v2 → contracts/
└── scripts/
    └── run_backtest.py     # CLI: --strategy, --ledger, backtest + export v2
```

---

## Dependencies

- **pandas** — OHLCV DataFrames, series indexing.
- **ccxt** — 4H candle fetch (exchange-agnostic).
- **pyyaml** — Strategy config (YAML).

No execution or exchange-specific logic beyond data fetch; execution is handled by downstream engines (e.g. binance-execution-engine) that read `contracts/strategy_spec.json`.
