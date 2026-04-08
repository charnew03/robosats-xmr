from datetime import UTC, datetime, timedelta

from backend.repository import InMemoryTradeRepository
from backend.sweeper import sweep_stale_trades
from backend.trade_engine import Trade, TradeState


def test_sweeper_cancels_old_created_and_funds_pending_trades() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo = InMemoryTradeRepository()

    old_created = Trade(trade_id="s1", amount_xmr=0.1, seller_id="seller")
    old_created.created_at = now - timedelta(hours=30)
    old_created.updated_at = old_created.created_at
    repo.save(old_created)

    old_pending = Trade(trade_id="s2", amount_xmr=0.1, seller_id="seller")
    old_pending.assign_deposit_address("48xmrS2")
    old_pending.updated_at = now - timedelta(hours=3)
    repo.save(old_pending)

    fresh = Trade(trade_id="s3", amount_xmr=0.1, seller_id="seller")
    fresh.created_at = now - timedelta(hours=1)
    fresh.updated_at = fresh.created_at
    repo.save(fresh)

    stats = sweep_stale_trades(repo, now=now)

    assert stats.cancelled == 2
    assert repo.get("s1").state == TradeState.CANCELLED
    assert repo.get("s2").state == TradeState.CANCELLED
    assert repo.get("s3").state == TradeState.CREATED

