"""Primitives for mid-frequency trade engine: EventCandidate, TradeSetup (proposal), Order (execution contract)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal


@dataclass(frozen=True)
class EventCandidate:
    """Detector output: event + features. Risk/sizing modules produce stop, tp, size; assembly builds TradeSetup."""

    asset: str
    side: Literal["long", "short"]
    entry_price: float
    features: Dict[str, Any] = field(default_factory=dict)  # e.g. atr, ema_fast, ema_slow
    invalidation: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class TradeSetup:
    """Setup detector output. Proposal only; state machine decides enter/exit."""

    asset: str
    side: Literal["long", "short"]
    entry: float
    stop_loss: float
    take_profit: float
    invalidation: str
    confidence: float
    size: float = 1.0


@dataclass
class Order:
    """Execution contract: written to strategy_spec.orders (v2)."""

    asset: str
    side: str  # "buy" | "sell"
    entry: float
    stop_loss: float
    take_profit: float
    size: float

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "side": self.side,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "size": self.size,
        }
