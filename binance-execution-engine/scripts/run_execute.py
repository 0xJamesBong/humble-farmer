#!/usr/bin/env python3
"""Run Binance rebalance: load strategy_spec, fetch balances, compute orders, dry-run or execute."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running from repo root or from binance-execution-engine
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from binance_execution_engine.config import (
    default_strategy_spec_path,
    get_target_weights,
    load_strategy_spec,
    SYMBOL_TO_PAIR,
)
from binance_execution_engine.balances import connect, fetch_balances_and_prices
from binance_execution_engine.rebalance import compute_orders
from binance_execution_engine.execute import run_orders


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute rebalance on Binance from strategy_spec.json")
    parser.add_argument(
        "--strategy-spec",
        type=Path,
        default=None,
        help="Path to strategy_spec.json (default: repo contracts/strategy_spec.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Only print orders (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Place live market orders (disables dry-run)",
    )
    parser.add_argument(
        "--exchange",
        default="binance",
        help="CCXT exchange id (default: binance)",
    )
    args = parser.parse_args()

    dry_run = not args.execute
    spec_path = args.strategy_spec or default_strategy_spec_path()

    if not spec_path.exists():
        print(f"Error: strategy_spec not found: {spec_path}", file=sys.stderr)
        return 1

    spec = load_strategy_spec(spec_path)
    target_weights = get_target_weights(spec)
    symbols = list(target_weights.keys())
    for s in symbols:
        if s not in SYMBOL_TO_PAIR:
            print(f"Error: symbol {s} not in symbol map", file=sys.stderr)
            return 1

    api_key = os.environ.get("BINANCE_API_KEY")
    secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not secret:
        print("Error: set BINANCE_API_KEY and BINANCE_API_SECRET", file=sys.stderr)
        return 1

    exchange = connect(exchange_id=args.exchange, api_key=api_key, secret=secret)
    balances, prices_usdt, total_usdt = fetch_balances_and_prices(exchange, symbols)

    print(f"Portfolio value (USDT): {total_usdt:.2f}")
    print(f"Target weights: {target_weights}")
    orders = compute_orders(target_weights, balances, prices_usdt, total_usdt)

    if not orders:
        print("No orders to place (already balanced or below min notional).")
        return 0

    print(f"Orders ({len(orders)}):" if dry_run else "Executing:")
    run_orders(exchange, orders, dry_run=dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
