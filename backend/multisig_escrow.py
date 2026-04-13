from __future__ import annotations

import json
import os
from typing import Protocol

from backend.trade_engine import Trade


MULTISIG_MODE = "MULTISIG_2OF3"
LEGACY_MODE = "LEGACY_SUBADDRESS"


def escrow_mode_from_env() -> str:
    """
    Default is 2-of-3 multisig-style trade escrow (buyer + seller + coordinator).

    Set ``ROBOSATS_XMR_ESCROW_MODE`` to ``legacy``, ``custodial``, ``subaddress``, or ``single``
    to use the older single coordinator subaddress per trade (community criticism: full custodial).
    """
    raw = os.getenv("ROBOSATS_XMR_ESCROW_MODE", "").strip().lower()
    if raw in ("legacy", "custodial", "subaddress", "single"):
        return LEGACY_MODE
    if raw in ("multisig", "multisig_2of3", "2of3"):
        return MULTISIG_MODE
    # Unset or unknown → multisig (preferred product default).
    return MULTISIG_MODE


class MultisigEscrowWallet(Protocol):
    """Optional wallet surface for 2-of-3 trade escrow (buyer + seller + coordinator)."""

    def allocate_multisig_trade_escrow(
        self, trade_id: str, seller_id: str, buyer_id: str | None
    ) -> tuple[str, str]: ...


def assign_multisig_bonds_if_enabled(trade: Trade, wallet: object, *, forced_mode: str | None = None) -> bool:
    """
    When multisig mode is default, allocate distinct 2-of-3-style bond receive addresses
    (same trust model as escrow: metadata + dedicated coordinator-derived addresses).
    """
    mode = forced_mode or escrow_mode_from_env()
    if mode != MULTISIG_MODE:
        return False
    allocator = getattr(wallet, "allocate_multisig_bond", None)
    if not callable(allocator):
        return False
    maker_addr, maker_info = allocator(trade.trade_id, "maker")
    taker_addr, taker_info = allocator(trade.trade_id, "taker")
    trade.maker_bond_address = maker_addr
    trade.taker_bond_address = taker_addr
    base: dict = {}
    if trade.multisig_info:
        try:
            parsed = json.loads(trade.multisig_info)
            if isinstance(parsed, dict):
                base = parsed
        except json.JSONDecodeError:
            base = {}
    try:
        maker_obj = json.loads(maker_info)
        taker_obj = json.loads(taker_info)
    except json.JSONDecodeError:
        maker_obj = {}
        taker_obj = {}
    base["bonds"] = {"maker": maker_obj, "taker": taker_obj}
    trade.multisig_info = json.dumps(base, separators=(",", ":"))
    return True


def assign_multisig_deposit_if_enabled(
    trade: Trade, wallet: object, *, forced_mode: str | None = None
) -> bool:
    """
    When escrow mode is multisig and the wallet supports it, assign deposit from multisig path.
    Returns True if multisig assignment was applied.
    """
    mode = forced_mode or escrow_mode_from_env()
    if mode != MULTISIG_MODE:
        return False
    allocator = getattr(wallet, "allocate_multisig_trade_escrow", None)
    if not callable(allocator):
        return False
    address, info_json = allocator(
        trade.trade_id,
        trade.seller_id,
        trade.buyer_id or "",
    )
    trade.assign_deposit_address(
        address,
        escrow_mode=MULTISIG_MODE,
        multisig_info=info_json,
    )
    return True


def multisig_escrow_summary(info_json: str | None) -> dict | None:
    if not info_json:
        return None
    try:
        return json.loads(info_json)
    except json.JSONDecodeError:
        return None
