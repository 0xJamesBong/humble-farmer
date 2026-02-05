"""Strategy building blocks: detectors, risk, sizing, and configs."""

from .risk import compute_stop_tp
from .setups import MIN_BARS, detect_event, detect_setup
from .sizing import compute_size
from .strategy_loader import load_strategy, strategies_dir

__all__ = [
    "compute_stop_tp",
    "MIN_BARS",
    "detect_event",
    "detect_setup",
    "compute_size",
    "load_strategy",
    "strategies_dir",
]
