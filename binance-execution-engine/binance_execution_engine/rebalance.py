"""Compute rebalance orders: target_weights vs current weights -> order list."""

from __future__ import annotations

from typing import Dict, List, NamedTuple

from .config import SYMBOL_TO_PAIR


class Order(NamedTuple):
    """Single market order: side, CCXT symbol (pair), size in base currency."""

    side: str  # "buy" or "sell"
    symbol: str  # e.g. "SOL/USDT"
    amount: float  # base currency amount


def compute_orders(
    target_weights: Dict[str, float],
    balances: Dict[str, float],
    prices_usdt: Dict[str, float],
    total_usdt: float,
    min_notional_usdt: float = 10.0,
) -> List[Order]:
    """
    Given target weights, current balances and prices, and total portfolio value in USDT,
    compute list of market orders to rebalance. Only allowlisted symbols (in target_weights
    and SYMBOL_TO_PAIR) are used. Orders below min_notional_usdt are skipped.
    """
    if total_usdt <= 0:
        return []

    orders: List[Order] = []
    for sym, target_w in target_weights.items():
        pair = SYMBOL_TO_PAIR.get(sym)
        if pair is None:
            continue  # USDT: no pair to trade
        current_value = balances.get(sym, 0) * prices_usdt.get(sym, 0)
        current_w = current_value / total_usdt if total_usdt else 0
        delta_w = target_w - current_w
        delta_usdt = delta_w * total_usdt
        if abs(delta_usdt) < min_notional_usdt:
            continue
        price = prices_usdt.get(sym, 0)
        if price <= 0:
            continue
        amount = abs(delta_usdt) / price
        side = "buy" if delta_usdt > 0 else "sell"
        orders.append(Order(side=side, symbol=pair, amount=amount))

    return orders
