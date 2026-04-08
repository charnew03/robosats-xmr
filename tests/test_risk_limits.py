import pytest

from backend.repository import InMemoryTradeRepository
from backend.risk_limits import RiskLimits, count_open_trades_for_seller, enforce_seller_open_trade_limit
from backend.trade_engine import Trade, TradeState


def test_count_open_trades_for_seller_counts_open_states() -> None:
    repo = InMemoryTradeRepository()
    t1 = Trade(trade_id="r1", amount_xmr=0.1, seller_id="s")
    t2 = Trade(trade_id="r2", amount_xmr=0.1, seller_id="s")
    t2.assign_deposit_address("48xmrAddr")
    t3 = Trade(trade_id="r3", amount_xmr=0.1, seller_id="s")
    t3.transition(TradeState.FUNDS_PENDING, reason="manual")
    t3.transition(TradeState.FUNDED, reason="manual")
    t3.transition(TradeState.FIAT_MARKED_PAID, reason="manual")
    t3.transition(TradeState.RELEASED, reason="manual")

    repo.save(t1)
    repo.save(t2)
    repo.save(t3)

    assert count_open_trades_for_seller(repo, "s") == 2


def test_enforce_open_trade_limit_blocks_at_limit() -> None:
    repo = InMemoryTradeRepository()
    repo.save(Trade(trade_id="r1", amount_xmr=0.1, seller_id="s"))
    repo.save(Trade(trade_id="r2", amount_xmr=0.1, seller_id="s"))
    limits = RiskLimits(max_open_trades_per_seller=2)

    with pytest.raises(ValueError):
        enforce_seller_open_trade_limit(repo, "s", limits)

