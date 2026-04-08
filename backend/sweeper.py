from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC, timedelta

from backend.repository import TradeRepository
from backend.trade_engine import TradeState


@dataclass(frozen=True)
class SweeperStats:
    cancelled: int


def sweep_stale_trades(
    repository: TradeRepository,
    *,
    now: datetime | None = None,
    created_timeout: timedelta = timedelta(hours=24),
    funds_pending_timeout: timedelta = timedelta(hours=2),
) -> SweeperStats:
    ts = datetime.now(UTC) if now is None else now
    cancelled = 0

    for trade in repository.list_all():
        if trade.state == TradeState.CREATED:
            if trade.created_at <= ts - created_timeout:
                trade.cancel("stale: created timeout")
                repository.save(trade)
                cancelled += 1
        elif trade.state == TradeState.FUNDS_PENDING:
            if trade.updated_at <= ts - funds_pending_timeout:
                trade.cancel("stale: funds pending timeout")
                repository.save(trade)
                cancelled += 1

    return SweeperStats(cancelled=cancelled)

