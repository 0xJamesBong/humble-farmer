"""Setup detectors: price history -> Optional[TradeSetup] or Optional[EventCandidate]. Registry for strategy-as-data."""

from __future__ import annotations

from typing import Callable, Dict, Optional, Any

import pandas as pd

from .types import EventCandidate, TradeSetup

# EMA spans for inflection detector
EMA_FAST_SPAN = 8
EMA_SLOW_SPAN = 21
MIN_BARS = EMA_SLOW_SPAN + 2

# Detector registry: detector_id -> (df, symbol, **params) -> Optional[EventCandidate]
DETECTOR_REGISTRY: Dict[str, Callable[..., Optional[EventCandidate]]] = {}


def ema_inflection_core(
    df: pd.DataFrame,
    asset: str = "SOL",
    fast: int = EMA_FAST_SPAN,
    slow: int = EMA_SLOW_SPAN,
) -> Optional[EventCandidate]:
    """
    Zero-crossing + slope: fast EMA crosses above slow EMA with positive slope -> long event.
    Returns EventCandidate or None. Risk/sizing applied by caller.
    """
    min_bars = slow + 2
    if len(df) < min_bars:
        return None
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    slope = diff.diff()
    last = len(df) - 1
    if diff.iloc[last - 1] < 0 and diff.iloc[last] > 0 and slope.iloc[last] > 0:
        entry_price = float(df["close"].iloc[last])
        return EventCandidate(
            asset=asset,
            side="long",
            entry_price=entry_price,
            features={"ema_fast": float(ema_fast.iloc[last]), "ema_slow": float(ema_slow.iloc[last])},
            invalidation="ema_diff_reverses",
            confidence=0.7,
        )
    return None


def _ema_inflection_registry(
    df: pd.DataFrame, symbol: str, **params: Any
) -> Optional[EventCandidate]:
    """Registry entry: symbol -> asset, pass params to ema_inflection_core."""
    asset = symbol.split("/")[0] if "/" in symbol else symbol
    return ema_inflection_core(df, asset=asset, **params)


def ema_inflection(df: pd.DataFrame, asset: str = "SOL") -> Optional[TradeSetup]:
    """
    Zero-crossing + slope: fast EMA crosses above slow EMA with positive slope -> long setup.
    Returns full TradeSetup (backward compat: hardcoded stop/tp/size). No execution; proposal only.
    """
    ev = ema_inflection_core(df, asset=asset)
    if ev is None:
        return None
    entry = ev.entry_price
    return TradeSetup(
        asset=ev.asset,
        side=ev.side,
        entry=entry,
        stop_loss=entry * 0.985,
        take_profit=entry * 1.03,
        invalidation=ev.invalidation,
        confidence=ev.confidence,
        size=1.0,
    )


def detect_setup(df: pd.DataFrame, symbol: str = "SOL/USDT") -> Optional[TradeSetup]:
    """
    Run setup detectors; return one proposal per bar or None.
    symbol is CCXT symbol (e.g. SOL/USDT); asset is extracted (SOL).
    """
    asset = symbol.split("/")[0] if "/" in symbol else symbol
    return ema_inflection(df, asset=asset)


def detect_event(
    df: pd.DataFrame, symbol: str, detector_id: str, **params: Any
) -> Optional[EventCandidate]:
    """
    Run registered detector by id; return EventCandidate or None.
    Used when strategy config is present (assembly then applies risk + sizing).
    """
    fn = DETECTOR_REGISTRY.get(detector_id)
    if fn is None:
        return None
    return fn(df, symbol, **params)


# Register built-in detectors
DETECTOR_REGISTRY["ema_inflection"] = _ema_inflection_registry
