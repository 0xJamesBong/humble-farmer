"""Backtest reporting: compute performance metrics from a Ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import sqrt
from pathlib import Path
from typing import Any, Iterable, List, Optional, Union

from .ledger import CompletedTrade, Ledger


def _iso(ts: Optional[datetime]) -> Optional[str]:
    if ts is None:
        return None
    return ts.isoformat()


def _trade_pnl_net(trade: CompletedTrade) -> float:
    return trade.pnl_gross - trade.fees


def _equity_curve(trades: List[CompletedTrade], starting_balance: float) -> List[dict[str, Any]]:
    equity = starting_balance
    curve = []
    for t in sorted(trades, key=lambda x: x.exit_ts):
        pnl = _trade_pnl_net(t)
        equity += pnl
        curve.append(
            {
                "timestamp": t.exit_ts.isoformat(),
                "equity": equity,
                "pnl_net": pnl,
                "asset": t.asset,
            }
        )
    return curve


def _max_drawdown(equity_values: Iterable[float]) -> dict[str, Optional[float]]:
    peak = None
    max_dd_abs = 0.0
    max_dd_pct = 0.0
    for value in equity_values:
        if peak is None or value > peak:
            peak = value
        if peak is None or peak == 0:
            continue
        dd_abs = peak - value
        dd_pct = dd_abs / peak
        if dd_abs > max_dd_abs:
            max_dd_abs = dd_abs
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
    if peak is None:
        return {"max_drawdown_abs": None, "max_drawdown_pct": None}
    return {"max_drawdown_abs": max_dd_abs, "max_drawdown_pct": max_dd_pct}


def _sharpe_sortino(returns: List[float]) -> dict[str, Optional[float]]:
    if len(returns) < 2:
        return {"sharpe": None, "sortino": None}
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = variance ** 0.5
    downside = [r for r in returns if r < 0]
    if std == 0:
        sharpe = None
    else:
        sharpe = (mean / std) * sqrt(len(returns))
    if len(downside) < 2:
        sortino = None
    else:
        d_mean = sum(downside) / len(downside)
        d_var = sum((r - d_mean) ** 2 for r in downside) / (len(downside) - 1)
        d_std = d_var ** 0.5
        sortino = (mean / d_std) * sqrt(len(returns)) if d_std != 0 else None
    return {"sharpe": sharpe, "sortino": sortino}


def _metrics_for_trades(
    trades: List[CompletedTrade],
    starting_balance: float,
) -> dict[str, Any]:
    trades_sorted = sorted(trades, key=lambda t: t.exit_ts)
    pnl_net = [_trade_pnl_net(t) for t in trades_sorted]
    total_pnl_net = sum(pnl_net)
    total_trades = len(trades_sorted)

    if total_trades == 0:
        return {
            "total_trades": 0,
            "total_pnl_net": 0.0,
            "total_return": 0.0 if starting_balance > 0 else None,
            "win_rate": None,
            "profit_factor": None,
            "avg_trade": None,
            "avg_win": None,
            "avg_loss": None,
            "max_drawdown_abs": None,
            "max_drawdown_pct": None,
            "sharpe": None,
            "sortino": None,
            "cagr": None,
            "exposure_time_pct": None,
            "avg_trade_duration_hours": None,
            "period_start_utc": None,
            "period_end_utc": None,
            "equity_curve": [],
        }

    wins = [p for p in pnl_net if p > 0]
    losses = [p for p in pnl_net if p < 0]
    win_rate = len(wins) / total_trades if total_trades > 0 else None
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    profit_factor = gross_profit / abs(gross_loss) if gross_loss < 0 else None
    avg_trade = total_pnl_net / total_trades
    avg_win = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None

    equity_curve = _equity_curve(trades_sorted, starting_balance)
    equity_values = [starting_balance] + [p["equity"] for p in equity_curve]
    drawdown = _max_drawdown(equity_values)

    returns = []
    equity_prev = starting_balance
    for p in pnl_net:
        if equity_prev != 0:
            returns.append(p / equity_prev)
        equity_prev += p
    sharpe_sortino = _sharpe_sortino(returns)

    period_start = min(t.entry_ts for t in trades_sorted)
    period_end = max(t.exit_ts for t in trades_sorted)
    total_seconds = (period_end - period_start).total_seconds()
    years = total_seconds / (365.25 * 24 * 3600) if total_seconds > 0 else 0.0
    ending_equity = starting_balance + total_pnl_net
    if years > 0 and starting_balance > 0 and ending_equity > 0:
        cagr = (ending_equity / starting_balance) ** (1 / years) - 1
    else:
        cagr = None

    exposure_seconds = sum((t.exit_ts - t.entry_ts).total_seconds() for t in trades_sorted)
    exposure_time_pct = exposure_seconds / total_seconds if total_seconds > 0 else None
    avg_trade_duration_hours = exposure_seconds / total_trades / 3600.0 if total_trades > 0 else None

    total_return = (ending_equity - starting_balance) / starting_balance if starting_balance > 0 else None

    return {
        "total_trades": total_trades,
        "total_pnl_net": total_pnl_net,
        "total_return": total_return,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade": avg_trade,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown_abs": drawdown["max_drawdown_abs"],
        "max_drawdown_pct": drawdown["max_drawdown_pct"],
        "sharpe": sharpe_sortino["sharpe"],
        "sortino": sharpe_sortino["sortino"],
        "cagr": cagr,
        "exposure_time_pct": exposure_time_pct,
        "avg_trade_duration_hours": avg_trade_duration_hours,
        "period_start_utc": _iso(period_start),
        "period_end_utc": _iso(period_end),
        "equity_curve": equity_curve,
    }


def generate_report(
    ledger: Ledger,
    starting_balance: float = 10_000.0,
) -> dict[str, Any]:
    """Generate report dict with overall + per-asset metrics."""
    trades = ledger.completed_trades
    assets = sorted({t.asset for t in trades})
    per_asset = {
        asset: _metrics_for_trades([t for t in trades if t.asset == asset], starting_balance)
        for asset in assets
    }
    overall = _metrics_for_trades(trades, starting_balance)
    now = datetime.now(timezone.utc)

    return {
        "generated_at_utc": now.isoformat(),
        "starting_balance": starting_balance,
        "metrics_basis": {
            "return_series": "per_trade",
            "annualization": "sqrt(n_trades)",
        },
        "overall": overall,
        "per_asset": per_asset,
        "ledger_summary": {
            "fills": len(ledger.fills),
            "completed_trades": len(ledger.completed_trades),
            "total_pnl_net": ledger.total_pnl_net,
        },
    }


def plot_pnl(
    ledger: Ledger,
    starting_balance: float = 10_000.0,
    save_path: Optional[Union[Path, str]] = None,
) -> None:
    """Plot equity curve (PnL over time). If save_path is None, display with plt.show()."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    trades = sorted(ledger.completed_trades, key=lambda t: t.exit_ts)
    if not trades:
        # No trades: flat line at starting_balance over a dummy time range
        fig, ax = plt.subplots(figsize=(10, 5))
        now = datetime.now(timezone.utc)
        t0, t1 = now - timedelta(days=1), now
        ax.plot([t0, t1], [starting_balance, starting_balance], color="gray", label="Equity")
        ax.set_ylabel("Equity")
        ax.set_title("PnL / Equity (no trades)")
        ax.legend()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))
        fig.autofmt_xdate()
        if save_path is not None:
            plt.savefig(save_path, bbox_inches="tight")
            plt.close(fig)
        else:
            plt.show()
        return

    curve = _equity_curve(trades, starting_balance)
    first_entry = min(t.entry_ts for t in trades)
    times = [first_entry] + [datetime.fromisoformat(p["timestamp"]) for p in curve]
    equity = [starting_balance] + [p["equity"] for p in curve]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, equity, color="steelblue", linewidth=2, label="Equity")
    ax.axhline(y=starting_balance, color="gray", linestyle="--", alpha=0.7, label="Starting balance")
    ax.set_ylabel("Equity")
    ax.set_title("PnL / Equity curve")
    ax.legend()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    plt.tight_layout()
    if save_path is not None:
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
