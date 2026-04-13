from __future__ import annotations

from typing import Protocol

from backend.multisig_escrow import assign_multisig_bonds_if_enabled
from backend.trade_engine import Trade


class BondSubaddressWallet(Protocol):
    """Minimal wallet surface for generating labeled subaddresses (same as funding wallet)."""

    def generate_subaddress(self, label: str) -> str: ...


def assign_trade_bonds(trade: Trade, wallet_rpc: BondSubaddressWallet) -> None:
    """
    Phase 3: allocate distinct subaddresses for maker (seller) and taker (buyer) bonds.

    Called during assign-deposit alongside the main trade escrow address. Amounts are
    set on trade creation; addresses are generated once and stored idempotently.
    """
    if trade.maker_bond_address is not None:
        return
    if assign_multisig_bonds_if_enabled(trade, wallet_rpc):
        return
    # Labels are unique per trade so wallet RPC / fake wallet produce distinct addresses.
    trade.maker_bond_address = wallet_rpc.generate_subaddress(
        f"{trade.trade_id}:maker_bond"
    )
    trade.taker_bond_address = wallet_rpc.generate_subaddress(
        f"{trade.trade_id}:taker_bond"
    )
