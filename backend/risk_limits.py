from __future__ import annotations

from dataclasses import dataclass

from backend.repository import TradeRepository
from backend.trade_engine import TradeState


@dataclass(frozen=True)
class RiskLimits:
    max_open_trades_per_seller: int = 3


def count_open_trades_for_seller(repository: TradeRepository, seller_id: str) -> int:
    open_states = {
        TradeState.CREATED,
        TradeState.FUNDS_PENDING,
        TradeState.FUNDED,
        TradeState.FIAT_MARKED_PAID,
        TradeState.DISPUTED,
    }
    return sum(
        1 for t in repository.list_all() if t.seller_id == seller_id and t.state in open_states
    )


def enforce_seller_open_trade_limit(
    repository: TradeRepository, seller_id: str, limits: RiskLimits
) -> None:
    open_count = count_open_trades_for_seller(repository, seller_id)
    if open_count >= limits.max_open_trades_per_seller:
        raise ValueError("seller has reached max open trades")
