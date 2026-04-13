from __future__ import annotations

"""
Non-custodial 2-of-3 escrow release (coordinator + buyer + seller).

Flow (see API routes under /trades/{id}/release-escrow/):
  1) prepare — coordinator wallet builds an unsigned multisig transfer (Monero: transfer
     with do_not_relay + multisig_txset; fake wallet: deterministic placeholder hex).
  2) sign — buyer and seller each paste the tx_data_hex produced by their own wallet
     after running sign_multisig against the previous blob (order: buyer, then seller).
     The server only stores and forwards the growing partial; it cannot forge peer keys.
  3) submit — coordinator wallet calls submit_multisig and records release_txid.

Bond returns (optional addresses on prepare) run after a successful on-chain submit,
same as legacy release-escrow.
"""

import json
from typing import Any, Literal

from backend.multisig_escrow import MULTISIG_MODE
from backend.trade_engine import Trade, TradeState

Party = Literal["buyer", "seller", "coordinator"]

RELEASE_IDLE = "idle"
RELEASE_PREPARED = "prepared"
RELEASE_AWAITING = "awaiting_signatures"
RELEASE_READY = "ready_to_submit"
RELEASE_SUBMITTED = "submitted"


def _parse_info(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _dump_info(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"))


def release_section(trade: Trade) -> dict[str, Any]:
    data = _parse_info(trade.multisig_info)
    rel = data.get("release")
    return rel if isinstance(rel, dict) else {}


def merge_release_into_trade(trade: Trade, release: dict[str, Any]) -> None:
    """Persist release workflow fields inside multisig_info JSON."""
    data = _parse_info(trade.multisig_info)
    prev = data.get("release")
    merged = {**(prev if isinstance(prev, dict) else {}), **release}
    data["release"] = merged
    trade.multisig_info = _dump_info(data)


def multisig_base_ready(trade: Trade) -> bool:
    """Escrow row has multisig metadata from deposit assignment."""
    if trade.escrow_mode != MULTISIG_MODE or not trade.deposit_address:
        return False
    data = _parse_info(trade.multisig_info)
    if data.get("threshold") != 2 or data.get("total") != 3:
        return False
    return True


def multisig_release_prepare_allowed(trade: Trade) -> bool:
    rel = release_section(trade)
    st = rel.get("status")
    return (
        trade.state == TradeState.FIAT_MARKED_PAID
        and multisig_base_ready(trade)
        and st in (None, "", RELEASE_IDLE)
    )


def fake_prepare_unsigned_hex(
    trade_id: str, buyer_payout_address: str, amount_xmr: float
) -> str:
    """Deterministic unsigned multisig placeholder for fake-wallet integration tests."""
    return (
        f"FAKE_MSIG_UNSIGNED|tid={trade_id}|to={buyer_payout_address[:24]}"
        f"|amt={amount_xmr}"
    )


def fake_apply_peer_signature(current_hex: str, party: Party, trade_id: str) -> str:
    """Append a simulated partial signature marker (fake wallet / dev only)."""
    if party not in ("buyer", "seller"):
        raise ValueError("only buyer and seller may submit independent partial signatures")
    if not current_hex.startswith("FAKE_MSIG_UNSIGNED|"):
        raise ValueError("invalid multisig tx state for signing")
    if party == "buyer" and "::SIG(buyer)" in current_hex:
        raise ValueError("buyer signature already applied")
    if party == "seller":
        if "::SIG(buyer)" not in current_hex:
            raise ValueError("buyer must sign before seller in the simulated multisig flow")
        if "::SIG(seller)" in current_hex:
            raise ValueError("seller signature already applied")
    return f"{current_hex}::SIG({party})|tid={trade_id}"


def multisig_submit_allowed(release: dict[str, Any]) -> bool:
    parties = set(release.get("signed_parties") or [])
    return (
        parties >= {"buyer", "seller"}
        and release.get("status") == RELEASE_READY
        and bool(release.get("tx_data_hex"))
    )


def release_status_for_trade(trade: Trade) -> str | None:
    if trade.escrow_mode != MULTISIG_MODE:
        return None
    rel = release_section(trade)
    st = rel.get("status")
    if st in (None, "", RELEASE_IDLE):
        return RELEASE_IDLE
    return str(st)


def pending_tx_hex_for_trade(trade: Trade) -> str | None:
    if trade.escrow_mode != MULTISIG_MODE:
        return None
    rel = release_section(trade)
    st = rel.get("status")
    if st in (RELEASE_PREPARED, RELEASE_AWAITING, RELEASE_READY):
        h = rel.get("tx_data_hex")
        return str(h) if h else None
    return None
