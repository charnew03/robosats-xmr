from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
