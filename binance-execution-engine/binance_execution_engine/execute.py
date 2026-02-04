"""Place market orders via CCXT (dry-run or live)."""

from __future__ import annotations

from typing import List

import ccxt

from .rebalance import Order


def run_orders(
    exchange: ccxt.Exchange,
    orders: List[Order],
    dry_run: bool = True,
) -> None:
    """
    Execute orders. If dry_run=True, only print what would be done.
    If dry_run=False, place market orders via CCXT.
    """
    for o in orders:
        if dry_run:
            print(f"  [dry-run] {o.side} {o.amount:.6f} {o.symbol}")
        else:
            if o.side == "buy":
                exchange.create_market_buy_order(o.symbol, o.amount)
            else:
                exchange.create_market_sell_order(o.symbol, o.amount)
            print(f"  executed: {o.side} {o.amount:.6f} {o.symbol}")
