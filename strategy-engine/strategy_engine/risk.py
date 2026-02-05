"""Risk module: compute stop_loss and take_profit from config. Pure functions."""

from __future__ import annotations

from typing import Any, Dict, Tuple, Union

import pandas as pd


def _atr(df: pd.DataFrame, span: int = 14) -> pd.Series:
    """ATR from high, low, close. Last value is scalar for current bar."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=span, adjust=False).mean()


def compute_stop_tp(
    entry_price: float,
    side: str,
    bar_or_df: Union[pd.Series, pd.DataFrame],
    risk_config: Dict[str, Any],
) -> Tuple[float, float]:
    """
    Compute stop_loss and take_profit from strategy risk config.
    risk_config: either {"pct": {"stop": 0.015, "take_profit": 0.03}} or
                 {"atr_mult": {"stop": 1.5, "take_profit": 2.0}} (and bar_or_df must have enough rows for ATR).
    Long: stop below entry, tp above. Short: stop above entry, tp below.
    Returns (stop_loss, take_profit).
    """
    if "pct" in risk_config:
        p = risk_config["pct"]
        stop_pct = float(p.get("stop", 0.015))
        tp_pct = float(p.get("take_profit", p.get("tp", 0.03)))
        if side == "long":
            stop_loss = entry_price * (1 - stop_pct)
            take_profit = entry_price * (1 + tp_pct)
        else:
            stop_loss = entry_price * (1 + stop_pct)
            take_profit = entry_price * (1 - tp_pct)
        return stop_loss, take_profit

    if "atr_mult" in risk_config:
        mult = risk_config["atr_mult"]
        stop_mult = float(mult.get("stop", 1.5))
        tp_mult = float(mult.get("take_profit", mult.get("tp", 2.0)))
        atr_span = int(mult.get("atr_span", 14))
        if isinstance(bar_or_df, pd.Series):
            # Single bar: need df for ATR; caller should pass df when using atr_mult
            raise ValueError("atr_mult requires DataFrame (multiple bars) for ATR; pass df")
        df = bar_or_df
        atr_series = _atr(df, span=atr_span)
        atr_val = float(atr_series.iloc[-1])
        if side == "long":
            stop_loss = entry_price - stop_mult * atr_val
            take_profit = entry_price + tp_mult * atr_val
        else:
            stop_loss = entry_price + stop_mult * atr_val
            take_profit = entry_price - tp_mult * atr_val
        return stop_loss, take_profit

    # Default: pct
    return compute_stop_tp(
        entry_price, side, bar_or_df, {"pct": {"stop": 0.015, "take_profit": 0.03}}
    )
