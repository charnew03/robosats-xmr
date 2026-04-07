from backend.wallet_adapter import check_wallet_health


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
