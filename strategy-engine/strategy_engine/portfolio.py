"""Signal -> target weights. Weights sum to 1.0."""

from __future__ import annotations

from typing import Any, Dict

# Allocation table: (trend, regime) -> weights for USDT, SOL, WBTC, WETH
# Weights must sum to 1.0
ALLOCATION: Dict[tuple, Dict[str, float]] = {
    ("up", "risk_on"): {"USDT": 0.1, "SOL": 0.35, "WBTC": 0.28, "WETH": 0.27},
    ("up", "risk_off"): {"USDT": 0.2, "SOL": 0.3, "WBTC": 0.25, "WETH": 0.25},
    ("down", "risk_on"): {"USDT": 0.4, "SOL": 0.2, "WBTC": 0.2, "WETH": 0.2},
    ("down", "risk_off"): {"USDT": 0.5, "SOL": 0.2, "WBTC": 0.15, "WETH": 0.15},
    ("neutral", "risk_on"): {"USDT": 0.2, "SOL": 0.3, "WBTC": 0.25, "WETH": 0.25},
    ("neutral", "risk_off"): {"USDT": 0.3, "SOL": 0.25, "WBTC": 0.225, "WETH": 0.225},
}


def signals_to_weights(signals: Dict[str, Any]) -> Dict[str, float]:
    """Map trend/regime signals to target portfolio weights. Keys: USDT, SOL, WBTC, WETH."""
    key = (signals.get("trend", "neutral"), signals.get("regime", "risk_off"))
    return ALLOCATION.get(key, ALLOCATION[("neutral", "risk_off")].copy())
