from __future__ import annotations

from dataclasses import dataclass, field

from backend.trade_engine import Trade


@dataclass
class InMemoryTradeRepository:
    _trades: dict[str, Trade] = field(default_factory=dict)

    def save(self, trade: Trade) -> Trade:
        self._trades[trade.trade_id] = trade
        return trade

    def get(self, trade_id: str) -> Trade | None:
        return self._trades.get(trade_id)
