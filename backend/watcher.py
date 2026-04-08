from __future__ import annotations

from dataclasses import dataclass
import logging
import time

from backend.funding_service import WalletFundingRPC, refresh_trade_funding
from backend.repository import TradeRepository
from backend.trade_engine import TradeState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WatcherRunStats:
    processed: int
    funded_now: int


@dataclass(frozen=True)
class WatcherLoopStats:
    iterations: int
    processed_total: int
    funded_total: int


def run_funding_refresh_once(
    repository: TradeRepository, wallet_rpc: WalletFundingRPC
) -> WatcherRunStats:
    processed = 0
    funded_now = 0

    for trade in repository.list_all():
        if trade.state != TradeState.FUNDS_PENDING:
            continue
        if trade.deposit_address is None:
            continue
        processed += 1
        try:
            is_now_funded = refresh_trade_funding(trade, wallet_rpc)
        except (RuntimeError, ValueError) as exc:
            logger.warning(
                "Watcher funding refresh failed for trade=%s address=%s: %s",
                trade.trade_id,
                trade.deposit_address,
                exc,
            )
            continue

        if is_now_funded:
            funded_now += 1
            logger.info(
                "Trade funded automatically: trade=%s confirmations=%s funded_at=%s",
                trade.trade_id,
                trade.current_confirmations,
                trade.funded_at.isoformat() if trade.funded_at else None,
            )
        repository.save(trade)

    return WatcherRunStats(processed=processed, funded_now=funded_now)


def run_funding_refresh_loop(
    repository: TradeRepository,
    wallet_rpc: WalletFundingRPC,
    interval_seconds: float = 10.0,
    max_iterations: int | None = None,
) -> WatcherLoopStats:
    iterations = 0
    processed_total = 0
    funded_total = 0

    while True:
        stats = run_funding_refresh_once(repository, wallet_rpc)
        iterations += 1
        processed_total += stats.processed
        funded_total += stats.funded_now

        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(interval_seconds)

    return WatcherLoopStats(
        iterations=iterations,
        processed_total=processed_total,
        funded_total=funded_total,
    )
