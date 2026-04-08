from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum


class TradeState(StrEnum):
    CREATED = "CREATED"
    FUNDS_PENDING = "FUNDS_PENDING"
    FUNDED = "FUNDED"
    FIAT_MARKED_PAID = "FIAT_MARKED_PAID"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"
    REFUNDED = "REFUNDED"


ALLOWED_TRANSITIONS: dict[TradeState, set[TradeState]] = {
    TradeState.CREATED: {TradeState.FUNDS_PENDING, TradeState.CANCELLED},
    TradeState.FUNDS_PENDING: {TradeState.FUNDED, TradeState.CANCELLED},
    TradeState.FUNDED: {
        TradeState.FIAT_MARKED_PAID,
        TradeState.DISPUTED,
        TradeState.REFUNDED,
    },
    TradeState.FIAT_MARKED_PAID: {TradeState.RELEASED, TradeState.DISPUTED},
    TradeState.DISPUTED: {TradeState.RELEASED, TradeState.REFUNDED},
    TradeState.RELEASED: set(),
    TradeState.CANCELLED: set(),
    TradeState.REFUNDED: set(),
}


@dataclass(frozen=True)
class TradeEvent:
    from_state: TradeState
    to_state: TradeState
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Trade:
    trade_id: str
    amount_xmr: float
    seller_id: str
    buyer_id: str | None = None
    deposit_address: str | None = None
    buyer_payout_address: str | None = None
    seller_refund_address: str | None = None
    release_txid: str | None = None
    refund_txid: str | None = None
    dispute_reason: str | None = None
    dispute_opened_at: datetime | None = None
    required_confirmations: int = 10
    current_confirmations: int = 0
    funded_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    state: TradeState = TradeState.CREATED
    events: list[TradeEvent] = field(default_factory=list)

    def transition(self, target_state: TradeState, reason: str) -> TradeEvent:
        if target_state not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(
                f"Invalid transition from {self.state} to {target_state}"
            )
        event = TradeEvent(from_state=self.state, to_state=target_state, reason=reason)
        self.events.append(event)
        self.state = target_state
        self.updated_at = datetime.now(UTC)
        if target_state == TradeState.FUNDED:
            self.funded_at = self.updated_at
        return event

    def assign_deposit_address(self, address: str) -> None:
        if not address:
            raise ValueError("address cannot be empty")
        if self.deposit_address is not None:
            raise ValueError("deposit address already assigned")
        if self.state != TradeState.CREATED:
            raise ValueError("deposit address can only be assigned from CREATED state")

        self.deposit_address = address
        self.transition(TradeState.FUNDS_PENDING, reason="deposit address assigned")

    def cancel(self, reason: str) -> TradeEvent:
        if not reason:
            raise ValueError("cancel reason cannot be empty")
        return self.transition(TradeState.CANCELLED, reason=reason)

    def mark_fiat_paid(self) -> TradeEvent:
        return self.transition(TradeState.FIAT_MARKED_PAID, reason="fiat marked paid")

    def open_dispute(self, reason: str) -> TradeEvent:
        if not reason:
            raise ValueError("dispute reason cannot be empty")
        self.dispute_reason = reason
        self.dispute_opened_at = datetime.now(UTC)
        return self.transition(TradeState.DISPUTED, reason="dispute opened")

    def record_confirmations(self, confirmations: int) -> bool:
        if confirmations < 0:
            raise ValueError("confirmations cannot be negative")
        self.current_confirmations = confirmations
        self.updated_at = datetime.now(UTC)

        if self.state == TradeState.FUNDS_PENDING and should_mark_funded(
            confirmations, self.required_confirmations
        ):
            self.transition(TradeState.FUNDED, reason="required confirmations reached")
            return True
        return False

    def set_release(self, payout_address: str, txid: str) -> None:
        if not payout_address:
            raise ValueError("payout address cannot be empty")
        if not txid:
            raise ValueError("txid cannot be empty")
        self.buyer_payout_address = payout_address
        self.release_txid = txid
        self.transition(TradeState.RELEASED, reason="released")

    def set_refund(self, refund_address: str, txid: str) -> None:
        if not refund_address:
            raise ValueError("refund address cannot be empty")
        if not txid:
            raise ValueError("txid cannot be empty")
        self.seller_refund_address = refund_address
        self.refund_txid = txid
        self.transition(TradeState.REFUNDED, reason="refunded")


def should_mark_funded(confirmations: int, required_confirmations: int = 10) -> bool:
    if confirmations < 0:
        raise ValueError("confirmations cannot be negative")
    return confirmations >= required_confirmations
