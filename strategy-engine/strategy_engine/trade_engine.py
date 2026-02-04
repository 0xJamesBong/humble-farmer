"""
Trade state machine: FLAT <-> OPEN. Setup proposes; state machine decides enter/exit.
All capital decisions live here; setup detectors never open/close.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

import pandas as pd

from .types import Order, TradeSetup


@dataclass
class Position:
    """Open position: same geometry as TradeSetup for exit logic."""

    asset: str
    side: Literal["long", "short"]
    entry: float
    stop_loss: float
    take_profit: float
    size: float


@dataclass
class TradeState:
    """State machine: FLAT or OPEN (with position)."""

    status: Literal["FLAT", "OPEN"]
    position: Optional[Position] = None


def initial_state() -> TradeState:
    return TradeState(status="FLAT", position=None)


def enter_trade(setup: TradeSetup) -> Tuple[List[Order], TradeState]:
    """
    If we are FLAT and accept setup: emit entry order, state -> OPEN.
    Caller must ensure state is FLAT; this does not check (single responsibility).
    """
    side = "buy" if setup.side == "long" else "sell"
    order = Order(
        asset=setup.asset,
        side=side,
        entry=setup.entry,
        stop_loss=setup.stop_loss,
        take_profit=setup.take_profit,
        size=setup.size,
    )
    pos = Position(
        asset=setup.asset,
        side=setup.side,
        entry=setup.entry,
        stop_loss=setup.stop_loss,
        take_profit=setup.take_profit,
        size=setup.size,
    )
    return [order], TradeState(status="OPEN", position=pos)


def manage_trade(state: TradeState, bar: pd.Series) -> Tuple[List[Order], TradeState]:
    """
    Given OPEN state and current bar (OHLC), check TP/SL. Emit exit order if hit; state -> FLAT.
    bar must have high, low, close. Long: TP when high >= take_profit, SL when low <= stop_loss.
    Short: TP when low <= take_profit, SL when high >= stop_loss.
    """
    if state.status != "OPEN" or state.position is None:
        return [], state

    pos = state.position
    high = float(bar["high"])
    low = float(bar["low"])

    if pos.side == "long":
        if low <= pos.stop_loss:
            # Stop out
            exit_order = Order(
                asset=pos.asset,
                side="sell",
                entry=pos.entry,
                stop_loss=pos.stop_loss,
                take_profit=pos.take_profit,
                size=pos.size,
            )
            return [exit_order], TradeState(status="FLAT", position=None)
        if high >= pos.take_profit:
            # Take profit
            exit_order = Order(
                asset=pos.asset,
                side="sell",
                entry=pos.entry,
                stop_loss=pos.stop_loss,
                take_profit=pos.take_profit,
                size=pos.size,
            )
            return [exit_order], TradeState(status="FLAT", position=None)
    else:
        if high >= pos.stop_loss:
            exit_order = Order(
                asset=pos.asset,
                side="buy",
                entry=pos.entry,
                stop_loss=pos.stop_loss,
                take_profit=pos.take_profit,
                size=pos.size,
            )
            return [exit_order], TradeState(status="FLAT", position=None)
        if low <= pos.take_profit:
            exit_order = Order(
                asset=pos.asset,
                side="buy",
                entry=pos.entry,
                stop_loss=pos.stop_loss,
                take_profit=pos.take_profit,
                size=pos.size,
            )
            return [exit_order], TradeState(status="FLAT", position=None)

    return [], state
