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
        return event


def should_mark_funded(confirmations: int, required_confirmations: int = 10) -> bool:
    if confirmations < 0:
        raise ValueError("confirmations cannot be negative")
    return confirmations >= required_confirmations
