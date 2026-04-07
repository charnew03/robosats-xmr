from __future__ import annotations


class FakeWalletFundingRPC:
    def __init__(self) -> None:
        self.confirmations_by_address: dict[str, int] = {}

    def generate_subaddress(self, trade_id: str) -> str:
        address = f"48xmr{trade_id[:8]}{len(self.confirmations_by_address) + 1}"
        self.confirmations_by_address.setdefault(address, 0)
        return address

    def get_confirmations(self, address: str) -> int:
        return self.confirmations_by_address.get(address, 0)
