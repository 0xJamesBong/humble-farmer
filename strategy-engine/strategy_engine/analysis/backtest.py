"""
Orchestrate: fetch 4H candles -> bar-by-bar loop -> detect_setup or (detect_event + risk + sizing) -> state machine -> orders + ledger.
Signals (setups) propose; state machine decides enter/exit. Returns (orders_last_bar, period_end, ledger).
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..data import fetch_4h_candles
from ..core.ledger import Ledger
from ..strategy.risk import compute_stop_tp
from ..strategy.setups import MIN_BARS, detect_event, detect_setup
from ..strategy.sizing import compute_size
from ..execution.trade_engine import _exit_reason, enter_trade, initial_state, manage_trade
from ..core.types import EventCandidate, Order, TradeSetup


def _bar_ts(bar: pd.Series) -> datetime:
    """Normalize bar timestamp to timezone-aware datetime."""
    ts = bar["timestamp"]
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _setup_from_config(
    event: EventCandidate,
    df_slice: pd.DataFrame,
    risk_config: Dict[str, Any],
    sizing_config: Dict[str, Any],
) -> TradeSetup:
    """Build TradeSetup from EventCandidate + risk + sizing (strategy-as-data path)."""
    stop_loss, take_profit = compute_stop_tp(
        event.entry_price, event.side, df_slice, risk_config
    )
    size = compute_size(sizing_config)
    return TradeSetup(
        asset=event.asset,
        side=event.side,
        entry=event.entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        invalidation=event.invalidation,
        confidence=event.confidence,
        size=size,
    )


def run_backtest(
    exchange_id: str,
    symbols: List[str],
    since_ts_ms: Optional[int] = None,
    limit: int = 500,
    state=None,
    fee_bps: float = 0.0,
    strategy_config: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Order], datetime, Ledger]:
    """
    Bar-by-bar backtest: fetch candles, loop from warmup to end; each bar run detect_setup
    (or detect_event + risk + sizing when strategy_config is set), then state machine.
    Record fills and completed trades to ledger.
    Returns (orders for last bar, period_end, ledger). If state is None, start FLAT.
    """
    candles = fetch_4h_candles(exchange_id, symbols, since_ts_ms, limit)
    if not candles:
        raise ValueError("No candles fetched")
    first_symbol = symbols[0]
    df = candles[first_symbol]
    if len(df) == 0:
        raise ValueError(f"No rows for {first_symbol}")

    warmup = MIN_BARS
    if len(df) <= warmup:
        raise ValueError(f"Need more than {warmup} bars; got {len(df)}")

    trade_state = state if state is not None else initial_state()
    ledger = Ledger()
    entry_bar_ts: Optional[datetime] = None  # set when we enter, used when we exit

    last_bar = df.iloc[-1]
    period_end = _bar_ts(last_bar)
    orders_last_bar: List[Order] = []

    for i in range(warmup, len(df)):
        df_slice = df.iloc[: i + 1]
        bar = df.iloc[i]
        bar_ts = _bar_ts(bar)
        close = float(bar["close"])
        fee = (fee_bps / 10000.0) * close  # fee in quote per unit; size in base, so fee on notional

        if strategy_config is not None:
            detector_id = strategy_config["entry"]["detector_id"]
            params = strategy_config["entry"].get("params", {})
            event = detect_event(df_slice, first_symbol, detector_id, **params)
            setup = (
                _setup_from_config(
                    event,
                    df_slice,
                    strategy_config["risk"],
                    strategy_config["sizing"],
                )
                if event is not None
                else None
            )
        else:
            setup = detect_setup(df_slice, symbol=first_symbol)
        orders_this_bar: List[Order] = []

        if trade_state.status == "FLAT" and setup is not None:
            orders_this_bar, trade_state = enter_trade(setup)
            entry_bar_ts = bar_ts
            for o in orders_this_bar:
                fill_price = close
                ledger.append_fill(
                    timestamp=bar_ts,
                    asset=o.asset,
                    side=o.side,
                    price=fill_price,
                    size=o.size,
                    fee=fee,
                )
        elif trade_state.status == "OPEN":
            pos = trade_state.position
            assert pos is not None
            orders_this_bar, new_state = manage_trade(trade_state, bar)
            if orders_this_bar and entry_bar_ts is not None:
                exit_reason = _exit_reason(bar, pos)
                for o in orders_this_bar:
                    fill_price = close
                    ledger.append_fill(
                        timestamp=bar_ts,
                        asset=o.asset,
                        side=o.side,
                        price=fill_price,
                        size=o.size,
                        fee=fee,
                        exit_reason=exit_reason,
                    )
                ledger.append_trade(
                    entry_ts=entry_bar_ts,
                    exit_ts=bar_ts,
                    asset=pos.asset,
                    side=pos.side,
                    entry_price=pos.entry,
                    exit_price=fill_price,
                    size=pos.size,
                    fees=fee * 2,  # entry + exit approx
                )
                entry_bar_ts = None
            trade_state = new_state

        if i == len(df) - 1:
            orders_last_bar = orders_this_bar

    return orders_last_bar, period_end, ledger
