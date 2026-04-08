from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from datetime import datetime, UTC, timedelta

from backend.repository import TradeRepository
from backend.trade_engine import TradeState


logger = logging.getLogger(__name__)


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
    """
    Cancel unfunded stale trades: CREATED past `created_timeout`, or FUNDS_PENDING
    with no funding activity past `funds_pending_timeout` (uses `updated_at`).
    """
    ts = datetime.now(UTC) if now is None else now
    cancelled = 0

    for trade in repository.list_all():
        if trade.state == TradeState.CREATED:
            if trade.created_at <= ts - created_timeout:
                reason = "stale: created timeout"
                trade.cancel(reason)
                repository.save(trade)
                cancelled += 1
                logger.info(
                    "Sweeper cancelled trade=%s state=CREATED reason=%s",
                    trade.trade_id,
                    reason,
                )
                if hasattr(repository, "add_audit_event"):
                    repository.add_audit_event(
                        trade.trade_id, "system", "sweeper_cancel", reason
                    )
        elif trade.state == TradeState.FUNDS_PENDING:
            if trade.updated_at <= ts - funds_pending_timeout:
                reason = "stale: funds pending timeout"
                trade.cancel(reason)
                repository.save(trade)
                cancelled += 1
                logger.info(
                    "Sweeper cancelled trade=%s state=FUNDS_PENDING reason=%s",
                    trade.trade_id,
                    reason,
                )
                if hasattr(repository, "add_audit_event"):
                    repository.add_audit_event(
                        trade.trade_id, "system", "sweeper_cancel", reason
                    )

    return SweeperStats(cancelled=cancelled)


@dataclass(frozen=True)
class SweeperLoopStats:
    iterations: int
    cancelled_total: int


def run_stale_trade_sweep_loop(
    repository: TradeRepository,
    *,
    interval_seconds: float = 300.0,
    max_iterations: int | None = None,
    now: datetime | None = None,
    created_timeout: timedelta = timedelta(hours=24),
    funds_pending_timeout: timedelta = timedelta(hours=2),
) -> SweeperLoopStats:
    """Background runner: periodic stale-trade sweep (same env pattern as funding watcher)."""
    iterations = 0
    cancelled_total = 0
    while True:
        stats = sweep_stale_trades(
            repository,
            now=now,
            created_timeout=created_timeout,
            funds_pending_timeout=funds_pending_timeout,
        )
        cancelled_total += stats.cancelled
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(interval_seconds)
    return SweeperLoopStats(
        iterations=iterations, cancelled_total=cancelled_total
    )

