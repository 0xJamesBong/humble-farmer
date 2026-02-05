"""Load strategy config from YAML/JSON. Single responsibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def _strategy_engine_root() -> Path:
    """strategy-engine package root (directory containing strategies/ and strategy_engine/)."""
    return Path(__file__).resolve().parents[2]


def strategies_dir() -> Path:
    """Default strategies directory at strategy-engine/strategies/."""
    return _strategy_engine_root() / "strategies"


def load_strategy(path: Path) -> Dict[str, Any]:
    """
    Load strategy config from YAML or JSON file.
    Returns dict with name, symbol, timeframe, entry (detector_id + params), risk, sizing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {path}")
    raw = path.read_text()
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        if not _HAS_YAML:
            raise ImportError("PyYAML required for YAML strategy files; pip install pyyaml")
        return yaml.safe_load(raw)
    if suffix == ".json":
        return json.loads(raw)
    raise ValueError(f"Unsupported strategy format: {suffix}; use .yaml or .json")
