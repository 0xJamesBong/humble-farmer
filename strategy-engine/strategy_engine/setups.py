"""Setup detectors: price history -> Optional[TradeSetup]. No weights, no execution."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .types import TradeSetup

# EMA spans for inflection detector
EMA_FAST_SPAN = 8
EMA_SLOW_SPAN = 21
MIN_BARS = EMA_SLOW_SPAN + 2


def ema_inflection(df: pd.DataFrame, asset: str = "SOL") -> Optional[TradeSetup]:
    """
    Zero-crossing + slope: fast EMA crosses above slow EMA with positive slope -> long setup.
    Returns TradeSetup or None. No execution; proposal only.
    """
    if len(df) < MIN_BARS:
        return None
    ema_fast = df["close"].ewm(span=EMA_FAST_SPAN, adjust=False).mean()
    ema_slow = df["close"].ewm(span=EMA_SLOW_SPAN, adjust=False).mean()
    diff = ema_fast - ema_slow
    slope = diff.diff()
    last = len(df) - 1
    if diff.iloc[last - 1] < 0 and diff.iloc[last] > 0 and slope.iloc[last] > 0:
        entry = float(df["close"].iloc[last])
        stop = entry * 0.985
        tp = entry * 1.03
        return TradeSetup(
            asset=asset,
            side="long",
            entry=entry,
            stop_loss=stop,
            take_profit=tp,
            invalidation="ema_diff_reverses",
            confidence=0.7,
            size=1.0,
        )
    return None


def detect_setup(df: pd.DataFrame, symbol: str = "SOL/USDT") -> Optional[TradeSetup]:
    """
    Run setup detectors; return one proposal per bar or None.
    symbol is CCXT symbol (e.g. SOL/USDT); asset is extracted (SOL).
    """
    asset = symbol.split("/")[0] if "/" in symbol else symbol
    return ema_inflection(df, asset=asset)
