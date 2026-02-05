"""Strategy engine: research, backtesting, and strategy_spec export. No Solana."""

from .analysis import generate_report, plot_pnl, run_backtest
from .io import export_strategy_spec_v2
from .strategy import compute_size, compute_stop_tp, detect_event, detect_setup, load_strategy, strategies_dir

__all__ = [
    "run_backtest",
    "generate_report",
    "plot_pnl",
    "export_strategy_spec_v2",
    "compute_size",
    "compute_stop_tp",
    "detect_event",
    "detect_setup",
    "load_strategy",
    "strategies_dir",
]
