import pytest

from backend.trade_engine import Trade, TradeState, should_mark_funded


def test_happy_path_trade_transitions() -> None:
    trade = Trade(trade_id="t-1")

    trade.transition(TradeState.FUNDS_PENDING, reason="escrow address assigned")
    trade.transition(TradeState.FUNDED, reason="10 confirmations reached")
    trade.transition(TradeState.FIAT_MARKED_PAID, reason="buyer marked fiat sent")
    trade.transition(TradeState.RELEASED, reason="seller confirmed fiat received")

    assert trade.state == TradeState.RELEASED
    assert len(trade.events) == 4


def test_invalid_transition_is_rejected() -> None:
    trade = Trade(trade_id="t-2")
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
