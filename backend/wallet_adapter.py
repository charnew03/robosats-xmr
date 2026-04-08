from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class EscrowReleaseWallet(Protocol):
    """Wallet capable of sending the trade escrow amount toward the buyer payout."""

    def release_escrow_to_buyer(
        self, deposit_subaddress: str, buyer_address: str, amount_xmr: float
    ) -> str: ...


def release_escrow_to_buyer(
    wallet: EscrowReleaseWallet,
    deposit_subaddress: str,
    buyer_address: str,
    amount_xmr: float,
) -> str:
    """
    Send `amount_xmr` from the trade's deposit subaddress to the buyer.

    Used by Phase 2 settlement; implementations may scope spends to the subaddress
    (real RPC) or simulate that in fake mode.
    """
    return wallet.release_escrow_to_buyer(
        deposit_subaddress, buyer_address, amount_xmr
    )


class WalletRPC(Protocol):
    def get_version(self) -> str: ...

    def is_synced(self) -> bool: ...


@dataclass(frozen=True)
class WalletHealth:
    rpc_reachable: bool
    wallet_version: str | None
    synced: bool


def check_wallet_health(wallet_rpc: WalletRPC) -> WalletHealth:
    try:
        version = wallet_rpc.get_version()
        synced = wallet_rpc.is_synced()
    except Exception:
        return WalletHealth(rpc_reachable=False, wallet_version=None, synced=False)

    return WalletHealth(
        rpc_reachable=True,
        wallet_version=version,
        synced=synced,
    )
