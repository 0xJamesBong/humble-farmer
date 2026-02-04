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
    """Extract target_weights from spec (v1). Keys: USDT, SOL, WBTC, WETH."""
    return dict(spec.get("target_weights", {}))


def get_spec_version(spec: Dict[str, Any]) -> int:
    """Strategy spec version: 1 = target_weights, 2 = orders."""
    return int(spec.get("version", 1))


def asset_to_pair(asset: str) -> str:
    """Map asset (e.g. SOL) to CCXT pair. Uses SYMBOL_TO_PAIR or fallback ASSET/USDT."""
    return SYMBOL_TO_PAIR.get(asset) or f"{asset}/USDT"


def _normalize_side(side: str) -> str:
    """Normalize side to CCXT: long -> buy, short -> sell; buy/sell unchanged."""
    if side in ("long", "buy"):
        return "buy"
    if side in ("short", "sell"):
        return "sell"
    return "buy"


def get_orders_v2(spec: Dict[str, Any]) -> list:
    """
    Extract orders from strategy_spec v2. Returns list of dicts with side, symbol, amount
    for execution (compatible with rebalance.Order shape: side, symbol, amount).
    Accepts side as "buy"/"sell" or "long"/"short".
    """
    raw = spec.get("orders", [])
    out = []
    for o in raw:
        asset = o.get("asset", "")
        pair = asset_to_pair(asset)
        out.append({
            "side": _normalize_side(o.get("side", "buy")),
            "symbol": pair,
            "amount": float(o.get("size", 0)),
        })
    return out
