"""Write strategy_spec.json to contracts/. Single responsibility."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

from .types import Order


def repo_root() -> Path:
    """Repo root: strategy-engine's parent."""
    return Path(__file__).resolve().parents[2]


def contracts_dir() -> Path:
    """contracts/ directory at repo root."""
    return repo_root() / "contracts"


def export_strategy_spec_v2(
    orders: List[Order],
    period_4h_end_utc: datetime,
    leverage_allowed: bool = False,
    output_path: Path | None = None,
) -> Path:
    """Build StrategySpec v2 (orders with lifecycle) and write to contracts/strategy_spec.json."""
    now = datetime.now(timezone.utc)
    spec = {
        "version": 2,
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period_4h_end_utc": period_4h_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "leverage_allowed": leverage_allowed,
        "orders": [o.to_dict() for o in orders],
    }
    path = output_path if output_path is not None else contracts_dir() / "strategy_spec.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)
    return path
