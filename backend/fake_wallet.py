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

    def send_xmr(self, address: str, amount_xmr: float) -> str:
        if not address or amount_xmr <= 0:
            raise ValueError("invalid send parameters")
        return f"fake-txid-{address[:6]}-{amount_xmr}"

    def release_escrow_to_buyer(
        self, deposit_subaddress: str, buyer_address: str, amount_xmr: float
    ) -> str:
        """Simulate spending from the trade deposit subaddress to the buyer."""
        if not deposit_subaddress or not buyer_address or amount_xmr <= 0:
            raise ValueError("invalid escrow release parameters")
        if deposit_subaddress not in self.confirmations_by_address:
            raise ValueError("unknown deposit subaddress for fake wallet")
        # Include from/to and exact amount so tests can assert end-to-end behavior.
        return (
            f"fake-escrow-from-{deposit_subaddress[:16]}-"
            f"to-{buyer_address[:12]}-amt-{amount_xmr}"
        )

    def release_bond(
        self, bond_subaddress: str, return_address: str, amount_xmr: float
    ) -> str:
        """Simulate returning a maker/taker bond from bond subaddress."""
        if not bond_subaddress or not return_address or amount_xmr <= 0:
            raise ValueError("invalid bond release parameters")
        if bond_subaddress not in self.confirmations_by_address:
            raise ValueError("unknown bond subaddress for fake wallet")
        return (
            f"fake-bond-from-{bond_subaddress[:16]}-"
            f"to-{return_address[:12]}-amt-{amount_xmr}"
        )
