"""Backtest ledger: fills and completed trades. Single responsibility."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class Fill:
    """Single fill: timestamp, asset, side, price, size, fee, optional exit_reason (sl/tp)."""

    timestamp: datetime
    asset: str
    side: str  # "buy" | "sell"
    price: float
    size: float
    fee: float = 0.0
    exit_reason: Optional[str] = None  # "sl" | "tp" for exits


@dataclass
class CompletedTrade:
    """Closed trade: entry and exit timestamps, asset, prices, size, pnl_gross, fees."""

    entry_ts: datetime
    exit_ts: datetime
    asset: str
    side: str  # "long" | "short"
    entry_price: float
    exit_price: float
    size: float
    pnl_gross: float
    fees: float


@dataclass
class Ledger:
    """Ledger of fills and completed trades. Built during bar-by-bar backtest."""

    fills: List[Fill] = field(default_factory=list)
    completed_trades: List[CompletedTrade] = field(default_factory=list)

    def append_fill(
        self,
        timestamp: datetime,
        asset: str,
        side: str,
        price: float,
        size: float,
        fee: float = 0.0,
        exit_reason: Optional[str] = None,
    ) -> None:
        self.fills.append(
            Fill(
                timestamp=timestamp,
                asset=asset,
                side=side,
                price=price,
                size=size,
                fee=fee,
                exit_reason=exit_reason,
            )
        )

    def append_trade(
        self,
        entry_ts: datetime,
        exit_ts: datetime,
        asset: str,
        side: str,
        entry_price: float,
        exit_price: float,
        size: float,
        fees: float = 0.0,
    ) -> None:
        if side == "long":
            pnl_gross = (exit_price - entry_price) * size
        else:
            pnl_gross = (entry_price - exit_price) * size
        self.completed_trades.append(
            CompletedTrade(
                entry_ts=entry_ts,
                exit_ts=exit_ts,
                asset=asset,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                size=size,
                pnl_gross=pnl_gross,
                fees=fees,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict (datetimes as ISO strings)."""
        return {
            "fills": [
                {
                    "timestamp": f.timestamp.isoformat(),
                    "asset": f.asset,
                    "side": f.side,
                    "price": f.price,
                    "size": f.size,
                    "fee": f.fee,
                    "exit_reason": f.exit_reason,
                }
                for f in self.fills
            ],
            "completed_trades": [
                {
                    "entry_ts": t.entry_ts.isoformat(),
                    "exit_ts": t.exit_ts.isoformat(),
                    "asset": t.asset,
                    "side": t.side,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "size": t.size,
                    "pnl_gross": t.pnl_gross,
                    "fees": t.fees,
                }
                for t in self.completed_trades
            ],
        }

    @property
    def total_pnl_net(self) -> float:
        """Total PnL after fees (from completed trades)."""
        return sum(t.pnl_gross - t.fees for t in self.completed_trades)
