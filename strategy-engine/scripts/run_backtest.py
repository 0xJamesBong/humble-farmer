#!/usr/bin/env python3
"""Run backtest with CCXT data and export strategy_spec.json (v2 orders) to contracts/."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from strategy_engine.backtest import run_backtest
from strategy_engine.export import export_strategy_spec_v2
from strategy_engine.report import generate_report, plot_pnl
from strategy_engine.strategy_loader import load_strategy, strategies_dir


DEFAULT_EXCHANGE = "binance"
DEFAULT_SYMBOLS = ["BTC/USDT"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest and export strategy_spec.json (v2 orders)")
    parser.add_argument(
        "--exchange",
        default=DEFAULT_EXCHANGE,
        help=f"CCXT exchange id (default: {DEFAULT_EXCHANGE})",
    )
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated symbols (default: BTC/USDT)",
    )
    parser.add_argument(
        "--since",
        type=int,
        default=None,
        help="Start time in ms (optional)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2000,
        help="Bars per symbol (default: 2000)",
    )
    parser.add_argument(
        "--fee-bps",
        type=float,
        default=0.0,
        help="Fee in basis points per fill (default: 0)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for strategy_spec.json (default: contracts/strategy_spec.json)",
    )
    parser.add_argument(
        "--ledger",
        nargs="?",
        const="-",
        default=None,
        metavar="PATH",
        help="Write ledger to JSON file (optional PATH); if --ledger with no PATH, print summary only",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write backtest report JSON (optional PATH)",
    )
    parser.add_argument(
        "--starting-balance",
        type=float,
        default=10_000.0,
        help="Starting balance for report metrics (default: 10000)",
    )
    parser.add_argument(
        "--strategy",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to strategy YAML/JSON (e.g. strategies/ema_inflection_v1.yaml); uses config symbol and detector+risk+sizing",
    )
    parser.add_argument(
        "--plot",
        nargs="?",
        const="-",
        default=None,
        metavar="PATH",
        help="Show PnL/equity graph: --plot to display, --plot out/pnl.png to save to file",
    )
    args = parser.parse_args()

    strategy_config = None
    if args.strategy is not None:
        path = args.strategy if args.strategy.is_absolute() else strategies_dir() / args.strategy.name
        strategy_config = load_strategy(path)
        symbols = [strategy_config["symbol"]]
    else:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    orders, period_end, ledger = run_backtest(
        exchange_id=args.exchange,
        symbols=symbols,
        since_ts_ms=args.since,
        limit=args.limit,
        fee_bps=args.fee_bps,
        strategy_config=strategy_config,
    )
    path = export_strategy_spec_v2(
        orders=orders,
        period_4h_end_utc=period_end,
        leverage_allowed=False,
        output_path=args.output,
    )
    print(f"Exported strategy_spec.json (v2, {len(orders)} orders) to {path}")

    if args.ledger is not None:
        if args.ledger == "-":
            print(
                f"Ledger: {len(ledger.fills)} fills, {len(ledger.completed_trades)} trades, "
                f"pnl_net={ledger.total_pnl_net:.4f}"
            )
        else:
            out_path = Path(args.ledger)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(ledger.to_dict(), f, indent=2)
            print(f"Ledger written to {out_path}")

    if args.report is not None:
        report = generate_report(ledger, starting_balance=args.starting_balance)
        out_path = Path(args.report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report written to {out_path}")

    if args.plot is not None:
        if args.plot == "-":
            # Show: save to out/pnl.png and open with system viewer (avoids hidden matplotlib window)
            save_path = Path("out/pnl.png")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plot_pnl(ledger, starting_balance=args.starting_balance, save_path=save_path)
            if sys.platform == "darwin":
                subprocess.run(["open", str(save_path)], check=False)
            elif sys.platform == "linux":
                subprocess.run(["xdg-open", str(save_path)], check=False)
            elif sys.platform == "win32":
                os.startfile(save_path)
            print(f"PnL graph saved to {save_path} and opened")
        else:
            save_path = Path(args.plot)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plot_pnl(ledger, starting_balance=args.starting_balance, save_path=save_path)
            print(f"PnL graph saved to {save_path}")


if __name__ == "__main__":
    main()
