"""Sizing module: compute position size from config. Pure functions."""

from __future__ import annotations

from typing import Any, Dict, Optional


def compute_size(
    sizing_config: Dict[str, Any],
    account_value: Optional[float] = None,
    volatility: Optional[float] = None,
) -> float:
    """
    Compute position size from strategy sizing config.
    sizing_config: {"fixed": 1.0} or {"fixed_risk": {"risk_pct": 0.005}}.
    For fixed_risk, account_value is used (risk_pct * account_value / risk_per_unit);
    if volatility or risk_per_unit not provided, falls back to fixed 1.0.
    Returns size in base currency units.
    """
    if "fixed" in sizing_config:
        return float(sizing_config["fixed"])

    if "fixed_risk" in sizing_config:
        fr = sizing_config["fixed_risk"]
        risk_pct = float(fr.get("risk_pct", 0.005))
        if account_value is not None and account_value > 0 and volatility is not None and volatility > 0:
            risk_amount = account_value * risk_pct
            return risk_amount / volatility
        return 1.0

    return 1.0
