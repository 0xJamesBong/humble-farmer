"""Fetch 4H OHLCV via CCXT. Research-only; no Solana."""

from __future__ import annotations

import pandas as pd
import ccxt
from typing import Dict, List, Optional


def fetch_4h_candles(
    exchange_id: str,
    symbols: List[str],
    since_ts_ms: Optional[int] = None,
    limit: int = 500,
) -> Dict[str, pd.DataFrame]:
    """Fetch 4H candles for each symbol. Returns symbol -> DataFrame with columns: timestamp, open, high, low, close, volume."""
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})
    result: Dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        ohlcv = exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe="4h",
            since=since_ts_ms,
            limit=limit,
        )
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        result[symbol] = df
    return result
