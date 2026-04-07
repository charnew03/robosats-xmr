from backend.repository import InMemoryTradeRepository
from backend.trade_engine import Trade, TradeState
from backend.watcher import run_funding_refresh_once


class FakeWalletRPC:
    def __init__(self, confirmations_by_address: dict[str, int]) -> None:
        self.confirmations_by_address = confirmations_by_address

    def generate_subaddress(self, trade_id: str) -> str:
        return f"48xmr{trade_id}"

    def get_confirmations(self, address: str) -> int:
        return self.confirmations_by_address.get(address, 0)


def test_watcher_processes_only_pending_funded_candidates() -> None:
    repo = InMemoryTradeRepository()

    funded_trade = Trade(trade_id="w1", amount_xmr=0.1, seller_id="s1")
    funded_trade.assign_deposit_address("48xmrw1")
    repo.save(funded_trade)

    already_released = Trade(trade_id="w2", amount_xmr=0.1, seller_id="s2")
    already_released.transition(TradeState.FUNDS_PENDING, reason="manual")
    already_released.transition(TradeState.FUNDED, reason="manual")
    already_released.transition(TradeState.FIAT_MARKED_PAID, reason="manual")
    already_released.transition(TradeState.RELEASED, reason="manual")
    repo.save(already_released)

    wallet = FakeWalletRPC(confirmations_by_address={"48xmrw1": 10})
    stats = run_funding_refresh_once(repo, wallet)

    refreshed = repo.get("w1")
    assert refreshed is not None
    assert refreshed.state == TradeState.FUNDED
    assert stats.processed == 1
    assert stats.funded_now == 1
