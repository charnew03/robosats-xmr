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


def should_mark_funded(confirmations: int, required_confirmations: int = 10) -> bool:
    if confirmations < 0:
        raise ValueError("confirmations cannot be negative")
    return confirmations >= required_confirmations
