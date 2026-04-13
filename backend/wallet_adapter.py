from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TransferActivity:
    confirmations: int
    total_received_xmr: float


class EscrowReleaseWallet(Protocol):
    """
    Wallet capable of sending the trade escrow amount toward the buyer payout.

    Multisig (2-of-3) trades use optional helpers on the concrete wallet implementation:
    ``prepare_multisig_escrow_unsigned`` (Monero: ``transfer`` + ``do_not_relay``),
    ``submit_multisig_release`` (Monero: ``submit_multisig``), and bond allocation via
    ``allocate_multisig_bond`` — see ``backend/multisig_release.py`` and API routes under
    ``/trades/{id}/release-escrow/``.
    """

    def release_escrow_to_buyer(
        self, deposit_subaddress: str, buyer_address: str, amount_xmr: float
    ) -> str: ...

    def release_bond(
        self, bond_subaddress: str, return_address: str, amount_xmr: float
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


def release_bond_to_owner(
    wallet: EscrowReleaseWallet,
    bond_subaddress: str,
    return_address: str,
    amount_xmr: float,
) -> str:
    """
    Return a bond amount from its dedicated bond subaddress to owner return address.
    """
    return wallet.release_bond(bond_subaddress, return_address, amount_xmr)


class WalletRPC(Protocol):
    def get_version(self) -> str: ...

    def is_synced(self) -> bool: ...


class FundingPollingWallet(Protocol):
    def get_confirmations(self, address: str) -> int: ...

    def get_transfer_activity(self, address: str) -> TransferActivity: ...


class SubaddressWallet(Protocol):
    def get_subaddress_index(self, address: str) -> int | None: ...


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


def reconcile_address_activity(
    wallet: FundingPollingWallet, address: str
) -> TransferActivity:
    """
    Reconcile inbound transfers for an address.

    Prefer wallet-native transfer polling (amount + confirmations). Fallback callers
    can still use `get_confirmations` behavior inside wallet implementations.
    """
    return wallet.get_transfer_activity(address)


def resolve_subaddress_index(wallet: SubaddressWallet, address: str) -> int | None:
    """Resolve subaddress minor index if wallet can map address->index."""
    return wallet.get_subaddress_index(address)
