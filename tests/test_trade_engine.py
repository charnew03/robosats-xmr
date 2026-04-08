import pytest

from backend.trade_engine import Trade, TradeState, should_mark_funded


def test_happy_path_trade_transitions() -> None:
    trade = Trade(trade_id="t-1", amount_xmr=0.25, seller_id="seller-1")

    trade.transition(TradeState.FUNDS_PENDING, reason="escrow address assigned")
    trade.transition(TradeState.FUNDED, reason="10 confirmations reached")
    trade.transition(TradeState.FIAT_MARKED_PAID, reason="buyer marked fiat sent")
    trade.transition(TradeState.RELEASED, reason="seller confirmed fiat received")

    assert trade.state == TradeState.RELEASED
    assert len(trade.events) == 4


def test_invalid_transition_is_rejected() -> None:
    trade = Trade(trade_id="t-2", amount_xmr=0.4, seller_id="seller-1")
    with pytest.raises(ValueError):
        trade.transition(TradeState.RELEASED, reason="skip states")


@pytest.mark.parametrize(
    ("confirmations", "expected"),
    [(0, False), (1, False), (9, False), (10, True), (12, True)],
)
def test_mark_funded_confirmation_threshold(confirmations: int, expected: bool) -> None:
    assert should_mark_funded(confirmations) is expected


def test_negative_confirmations_are_rejected() -> None:
    with pytest.raises(ValueError):
        should_mark_funded(-1)


def test_assign_deposit_address_moves_trade_to_funds_pending() -> None:
    trade = Trade(trade_id="t-3", amount_xmr=0.3, seller_id="seller-2")
    trade.assign_deposit_address("48xmrAddressTrade1")

    assert trade.deposit_address == "48xmrAddressTrade1"
    assert trade.state == TradeState.FUNDS_PENDING


def test_record_confirmations_marks_funded_at_threshold() -> None:
    trade = Trade(trade_id="t-4", amount_xmr=0.5, seller_id="seller-3")
    trade.assign_deposit_address("48xmrAddressTrade2")

    funded = trade.record_confirmations(10)

    assert funded is True
    assert trade.state == TradeState.FUNDED
    assert trade.funded_at is not None


def test_mark_fiat_paid_helper() -> None:
    trade = Trade(trade_id="t-5", amount_xmr=0.2, seller_id="seller-5")
    trade.assign_deposit_address("48xmrAddressTrade5")
    trade.record_confirmations(10)

    trade.mark_fiat_paid()

    assert trade.state == TradeState.FIAT_MARKED_PAID


def test_open_dispute_sets_reason_and_state() -> None:
    trade = Trade(trade_id="t-6", amount_xmr=0.2, seller_id="seller-6")
    trade.assign_deposit_address("48xmrAddressTrade6")
    trade.record_confirmations(10)

    trade.open_dispute("did not receive fiat")

    assert trade.state == TradeState.DISPUTED
    assert trade.dispute_reason == "did not receive fiat"
    assert trade.dispute_opened_at is not None
