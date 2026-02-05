"""Analysis layer: backtests and reporting."""

from .backtest import run_backtest
from .report import generate_report, plot_pnl

__all__ = ["run_backtest", "generate_report", "plot_pnl"]
