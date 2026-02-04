"""Load strategy_spec.json and symbol -> Binance pair map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

# Abstract symbols (from strategy_spec) -> Binance CCXT pair. None = quote (USDT), no pair.
SYMBOL_TO_PAIR: Dict[str, str | None] = {
    "USDT": None,
    "SOL": "SOL/USDT",
    "WBTC": "BTC/USDT",
    "WETH": "ETH/USDT",
}


def repo_root() -> Path:
    """Repo root: binance-execution-engine's parent."""
    return Path(__file__).resolve().parents[2]


def default_strategy_spec_path() -> Path:
    """Default path to strategy_spec.json at repo root contracts/."""
    return repo_root() / "contracts" / "strategy_spec.json"


def load_strategy_spec(path: Path | None = None) -> Dict[str, Any]:
    """Load and parse strategy_spec.json. Returns dict with version, target_weights, etc."""
    p = path if path is not None else default_strategy_spec_path()
    with open(p) as f:
        return json.load(f)


def get_target_weights(spec: Dict[str, Any]) -> Dict[str, float]:
    """Extract target_weights from spec. Keys: USDT, SOL, WBTC, WETH."""
    return dict(spec.get("target_weights", {}))
