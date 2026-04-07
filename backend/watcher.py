from __future__ import annotations

from dataclasses import dataclass

from backend.funding_service import WalletFundingRPC, refresh_trade_funding
from backend.repository import TradeRepository
from backend.trade_engine import TradeState


@dataclass(frozen=True)
class WatcherRunStats:
    processed: int
    funded_now: int


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
        if refresh_trade_funding(trade, wallet_rpc):
            funded_now += 1
        repository.save(trade)

    return WatcherRunStats(processed=processed, funded_now=funded_now)
