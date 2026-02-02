"""Trend and regime signals. Pure functions; no I/O."""

from __future__ import annotations

import pandas as pd
from typing import Any, Dict

# Default MA period for trend
DEFAULT_MA_PERIOD = 20


def trend(df: pd.DataFrame, ma_period: int = DEFAULT_MA_PERIOD) -> str:
    """Compute trend from close vs MA. Returns 'up', 'down', or 'neutral'."""
    if len(df) < ma_period:
        return "neutral"
    close = df["close"].iloc[-1]
    ma = df["close"].rolling(ma_period).mean().iloc[-1]
    if close > ma * 1.002:
        return "up"
    if close < ma * 0.998:
        return "down"
    return "neutral"


def regime(df: pd.DataFrame, lookback: int = 20) -> str:
    """Simple regime: volatility-based risk_on vs risk_off."""
    if len(df) < lookback:
        return "risk_off"
    recent = df["close"].pct_change().dropna().tail(lookback)
    vol = recent.std()
    if pd.isna(vol) or vol < 1e-8:
        return "risk_off"
    # Higher recent volatility -> risk_on
    median_vol = df["close"].pct_change().dropna().rolling(lookback).std().median()
    if pd.isna(median_vol) or vol > median_vol * 1.2:
        return "risk_on"
    return "risk_off"


def compute_signals(df: pd.DataFrame, ma_period: int = DEFAULT_MA_PERIOD) -> Dict[str, Any]:
    """Compute trend and regime from a single symbol's OHLCV. Returns dict for portfolio."""
    return {
        "trend": trend(df, ma_period),
        "regime": regime(df, ma_period),
    }
