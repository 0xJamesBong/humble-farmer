#!/usr/bin/env python3
"""Run backtest with CCXT data and export strategy_spec.json (v2 orders) to contracts/."""

from __future__ import annotations

import argparse
from pathlib import Path

from strategy_engine.backtest import run_backtest
from strategy_engine.export import export_strategy_spec_v2


DEFAULT_EXCHANGE = "binance"
DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest and export strategy_spec.json (v2 orders)")
    parser.add_argument(
        "--exchange",
        default=DEFAULT_EXCHANGE,
        help=f"CCXT exchange id (default: {DEFAULT_EXCHANGE})",
    )
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated symbols (default: BTC/USDT,ETH/USDT,SOL/USDT)",
    )
    parser.add_argument(
        "--since",
        type=int,
        default=None,
        help="Start time in ms (optional)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Bars per symbol (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for strategy_spec.json (default: contracts/strategy_spec.json)",
    )
    args = parser.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    orders, period_end = run_backtest(
        exchange_id=args.exchange,
        symbols=symbols,
        since_ts_ms=args.since,
        limit=args.limit,
    )
    path = export_strategy_spec_v2(
        orders=orders,
        period_4h_end_utc=period_end,
        leverage_allowed=False,
        output_path=args.output,
    )
    print(f"Exported strategy_spec.json (v2, {len(orders)} orders) to {path}")


if __name__ == "__main__":
    main()
