from backend.repository import InMemoryTradeRepository
from backend.trade_engine import Trade, TradeState
from backend.watcher import run_funding_refresh_loop, run_funding_refresh_once


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


def test_watcher_loop_aggregates_stats() -> None:
    repo = InMemoryTradeRepository()
    trade = Trade(trade_id="loop1", amount_xmr=0.1, seller_id="s1")
    trade.assign_deposit_address("48xmrloop1")
    repo.save(trade)

    wallet = FakeWalletRPC(confirmations_by_address={"48xmrloop1": 10})
    loop_stats = run_funding_refresh_loop(
        repository=repo,
        wallet_rpc=wallet,
        interval_seconds=0,
        max_iterations=2,
    )

    assert loop_stats.iterations == 2
    assert loop_stats.processed_total == 1
    assert loop_stats.funded_total == 1


def test_watcher_skips_already_funded_trade_on_later_polls() -> None:
    repo = InMemoryTradeRepository()
    trade = Trade(trade_id="skip1", amount_xmr=0.1, seller_id="s1")
    trade.assign_deposit_address("48xmrskip1")
    repo.save(trade)

    wallet = FakeWalletRPC(confirmations_by_address={"48xmrskip1": 12})
    first_run = run_funding_refresh_once(repo, wallet)
    second_run = run_funding_refresh_once(repo, wallet)

    refreshed = repo.get("skip1")
    assert refreshed is not None
    assert refreshed.state == TradeState.FUNDED
    assert first_run.processed == 1
    assert first_run.funded_now == 1
    assert second_run.processed == 0
    assert second_run.funded_now == 0
