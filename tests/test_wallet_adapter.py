from backend.fake_wallet import FakeWalletFundingRPC
from backend.wallet_adapter import (
    check_wallet_health,
    reconcile_address_activity,
    release_escrow_to_buyer,
    resolve_subaddress_index,
)


class HealthyWalletRPC:
    def get_version(self) -> str:
        return "0.18.3.4"

    def is_synced(self) -> bool:
        return True


class BrokenWalletRPC:
    def get_version(self) -> str:
        raise RuntimeError("connection refused")

    def is_synced(self) -> bool:
        return False


def test_wallet_health_success() -> None:
    health = check_wallet_health(HealthyWalletRPC())
    assert health.rpc_reachable is True
    assert health.wallet_version == "0.18.3.4"
    assert health.synced is True


def test_wallet_health_failure_graceful() -> None:
    health = check_wallet_health(BrokenWalletRPC())
    assert health.rpc_reachable is False
    assert health.wallet_version is None
    assert health.synced is False


def test_release_escrow_to_buyer_fake_wallet() -> None:
    wallet = FakeWalletFundingRPC()
    sub = wallet.generate_subaddress("trade-z")
    txid = release_escrow_to_buyer(wallet, sub, "48xmrBuyerAddr", 1.25)
    assert "fake-escrow-from-" in txid
    assert sub[:16] in txid


def test_reconcile_transfer_activity_and_subaddress_index_fake_wallet() -> None:
    wallet = FakeWalletFundingRPC()
    sub = wallet.generate_subaddress("trade-idx")
    wallet.confirmations_by_address[sub] = 7
    wallet.received_xmr_by_address[sub] = 0.42

    activity = reconcile_address_activity(wallet, sub)
    assert activity.confirmations == 7
    assert activity.total_received_xmr == 0.42
    assert resolve_subaddress_index(wallet, sub) is not None
