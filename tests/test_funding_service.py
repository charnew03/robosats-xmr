import pytest

from backend.funding_service import assign_trade_deposit, refresh_trade_funding
from backend.trade_engine import Trade, TradeState


class FakeWalletFundingRPC:
    def __init__(self, confirmations_by_address: dict[str, int]) -> None:
        self.confirmations_by_address = confirmations_by_address
        self.generated = 0

    def generate_subaddress(self, trade_id: str) -> str:
        self.generated += 1
        return f"48xmr{trade_id}{self.generated}"

    def get_confirmations(self, address: str) -> int:
        return self.confirmations_by_address.get(address, 0)


def test_assign_trade_deposit_assigns_address_and_transitions() -> None:
    trade = Trade(trade_id="t100", amount_xmr=0.7, seller_id="seller-100")
    wallet = FakeWalletFundingRPC(confirmations_by_address={})

    address = assign_trade_deposit(trade, wallet)

    assert address == trade.deposit_address
    assert trade.state == TradeState.FUNDS_PENDING


def test_refresh_trade_funding_marks_trade_funded_when_confirmed() -> None:
    trade = Trade(trade_id="t101", amount_xmr=0.9, seller_id="seller-101")
    wallet = FakeWalletFundingRPC(confirmations_by_address={})
    address = assign_trade_deposit(trade, wallet)
    wallet.confirmations_by_address[address] = 10

    funded = refresh_trade_funding(trade, wallet)

    assert funded is True
    assert trade.state == TradeState.FUNDED
    assert trade.current_confirmations == 10


def test_refresh_trade_funding_requires_deposit_address() -> None:
    trade = Trade(trade_id="t102", amount_xmr=0.12, seller_id="seller-102")
    wallet = FakeWalletFundingRPC(confirmations_by_address={})

    with pytest.raises(ValueError):
        refresh_trade_funding(trade, wallet)
