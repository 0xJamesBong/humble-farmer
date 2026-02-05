"""
Trade state machine: FLAT <-> OPEN. Setup proposes; state machine decides enter/exit.
All capital decisions live here; setup detectors never open/close.

Fill rule (same bar): If both stop_loss and take_profit could be hit in one bar,
we check STOP LOSS before TAKE PROFIT. So we exit on SL first (conservative).
Backtest and live must use this same rule for identical execution semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

import pandas as pd

from ..core.types import Order, TradeSetup


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


def _exit_reason(bar: pd.Series, position: Position) -> Optional[Literal["sl", "tp"]]:
    """
    Deterministic exit reason for current bar. SL is checked before TP (same-bar rule).
    Returns "sl", "tp", or None if no exit this bar.
    """
    high = float(bar["high"])
    low = float(bar["low"])
    if position.side == "long":
        if low <= position.stop_loss:
            return "sl"
        if high >= position.take_profit:
            return "tp"
    else:
        if high >= position.stop_loss:
            return "sl"
        if low <= position.take_profit:
            return "tp"
    return None


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
    Given OPEN state and current bar (OHLC), apply fill rule and exit if SL or TP hit.
    Uses _exit_reason (SL checked before TP same bar). Emit exit order if hit; state -> FLAT.
    """
    if state.status != "OPEN" or state.position is None:
        return [], state

    pos = state.position
    reason = _exit_reason(bar, pos)
    if reason is None:
        return [], state

    exit_side = "sell" if pos.side == "long" else "buy"
    exit_order = Order(
        asset=pos.asset,
        side=exit_side,
        entry=pos.entry,
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        size=pos.size,
    )
    return [exit_order], TradeState(status="FLAT", position=None)
