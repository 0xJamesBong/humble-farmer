"""
Orchestrate: fetch 4H candles -> detect_setup -> trade state machine -> orders.
Signals (setups) propose; state machine decides enter/exit. Return (orders, period_end).
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timezone
from typing import List, Tuple

from .data import fetch_4h_candles
from .setups import detect_setup
from .trade_engine import enter_trade, initial_state, manage_trade
from .types import Order


def run_backtest(
    exchange_id: str,
    symbols: List[str],
    since_ts_ms: int | None = None,
    limit: int = 500,
    state=None,
) -> Tuple[List[Order], datetime]:
    """
    Fetch 4H candles, run setup detection and trade state machine, return orders for this bar and period_4h_end_utc.
    If state is None, start FLAT (MVP in-memory). Otherwise use provided state (e.g. persisted OPEN).
    """
    candles = fetch_4h_candles(exchange_id, symbols, since_ts_ms, limit)
    if not candles:
        raise ValueError("No candles fetched")
    first_symbol = symbols[0]
    df = candles[first_symbol]
    if len(df) == 0:
        raise ValueError(f"No rows for {first_symbol}")

    last_bar = df.iloc[-1]
    last_ts = df.iloc[-1]["timestamp"]
    if hasattr(last_ts, "to_pydatetime"):
        period_end = last_ts.to_pydatetime()
    else:
        period_end = last_ts
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)

    trade_state = state if state is not None else initial_state()
    orders: List[Order] = []

    setup = detect_setup(df, symbol=first_symbol)

    if trade_state.status == "FLAT" and setup is not None:
        orders, trade_state = enter_trade(setup)
    elif trade_state.status == "OPEN":
        orders, trade_state = manage_trade(trade_state, last_bar)

    return orders, period_end
