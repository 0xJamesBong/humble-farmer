"""Minimal backtester over 4H bars. CCXT data -> signals -> portfolio -> latest weights."""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from .data import fetch_4h_candles
from .signals import compute_signals
from .portfolio import signals_to_weights


def run_backtest(
    exchange_id: str,
    symbols: List[str],
    since_ts_ms: int | None = None,
    limit: int = 500,
) -> Tuple[Dict[str, float], datetime]:
    """
    Fetch 4H candles, run signal + portfolio over bars, return latest target_weights and period_4h_end_utc.
    Uses the first symbol's last bar time as period_4h_end_utc; aggregates signals from all symbols (uses first for MVP).
    """
    candles = fetch_4h_candles(exchange_id, symbols, since_ts_ms, limit)
    if not candles:
        raise ValueError("No candles fetched")
    # Use first symbol's DataFrame for bar-by-bar loop; for MVP we only need last bar
    first_symbol = symbols[0]
    df = candles[first_symbol]
    if len(df) == 0:
        raise ValueError(f"No rows for {first_symbol}")
    # Optional: loop over bars for full backtest. For MVP we only need last row.
    last = df.iloc[-1]
    last_ts = last["timestamp"]
    if hasattr(last_ts, "to_pydatetime"):
        period_end = last_ts.to_pydatetime()
    else:
        period_end = last_ts
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    # Compute signals from full history up to last bar
    signals = compute_signals(df)
    weights = signals_to_weights(signals)
    return weights, period_end
