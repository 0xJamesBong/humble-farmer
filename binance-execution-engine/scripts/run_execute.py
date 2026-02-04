#!/usr/bin/env python3
"""Run Binance rebalance: load strategy_spec, fetch balances, compute orders, dry-run or execute."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running from repo root or from binance-execution-engine
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from binance_execution_engine.config import (
    default_strategy_spec_path,
    get_orders_v2,
    get_spec_version,
    get_target_weights,
    load_strategy_spec,
    repo_root,
    SYMBOL_TO_PAIR,
)
from binance_execution_engine.balances import connect, fetch_balances_and_prices
from binance_execution_engine.rebalance import Order as RebalanceOrder, compute_orders
from binance_execution_engine.execute import run_orders


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute on Binance from strategy_spec.json (v1 rebalance or v2 orders)")
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

    # Load .env from repo root so BINANCE_API_KEY / BINANCE_API_SECRET are set
    load_dotenv(repo_root() / ".env")

    dry_run = not args.execute
    spec_path = args.strategy_spec or default_strategy_spec_path()

    if not spec_path.exists():
        print(f"Error: strategy_spec not found: {spec_path}", file=sys.stderr)
        return 1

    spec = load_strategy_spec(spec_path)
    version = get_spec_version(spec)
    api_key = os.environ.get("BINANCE_API_KEY")
    secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not secret:
        print("Error: set BINANCE_API_KEY and BINANCE_API_SECRET", file=sys.stderr)
        return 1

    exchange = connect(exchange_id=args.exchange, api_key=api_key, secret=secret)

    if version == 2 and spec.get("orders"):
        # v2: discrete orders (entry/stop/take_profit/size)
        raw_orders = get_orders_v2(spec)
        orders = [RebalanceOrder(side=o["side"], symbol=o["symbol"], amount=o["amount"]) for o in raw_orders]
        if not orders:
            print("No orders in strategy_spec (v2).")
            return 0
        print(f"Strategy spec v2: {len(orders)} order(s)")
        print(f"Orders ({len(orders)}):" if dry_run else "Executing:")
        run_orders(exchange, orders, dry_run=dry_run)
        return 0

    # v1: rebalance from target_weights
    target_weights = get_target_weights(spec)
    symbols = list(target_weights.keys())
    for s in symbols:
        if s not in SYMBOL_TO_PAIR:
            print(f"Error: symbol {s} not in symbol map", file=sys.stderr)
            return 1
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
