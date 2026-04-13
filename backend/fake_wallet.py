from __future__ import annotations

import json

from backend.wallet_adapter import TransferActivity


class FakeWalletFundingRPC:
    def __init__(self) -> None:
        self.confirmations_by_address: dict[str, int] = {}
        self.received_xmr_by_address: dict[str, float] = {}
        self.subaddress_index_by_address: dict[str, int] = {}

    def get_version(self) -> str:
        return "fake-wallet"

    def is_synced(self) -> bool:
        return True

    def generate_subaddress(self, trade_id: str) -> str:
        next_index = len(self.confirmations_by_address) + 1
        address = f"48xmr{trade_id[:8]}{next_index}"
        self.confirmations_by_address.setdefault(address, 0)
        self.received_xmr_by_address.setdefault(address, 0.0)
        self.subaddress_index_by_address.setdefault(address, next_index)
        return address

    def allocate_multisig_bond(self, trade_id: str, role: str) -> tuple[str, str]:
        """
        Simulated 2-of-3 bond receive address (maker/taker); funds are tracked like escrow.
        """
        next_index = len(self.confirmations_by_address) + 1
        safe_role = (role or "x")[:12]
        address = f"45msig2of3bond{safe_role}{trade_id[:6]}{next_index}"
        self.confirmations_by_address.setdefault(address, 0)
        self.received_xmr_by_address.setdefault(address, 0.0)
        self.subaddress_index_by_address.setdefault(address, next_index)
        info = {
            "threshold": 2,
            "total": 3,
            "parties": ["seller", "buyer", "coordinator"],
            "role": safe_role,
            "trade_id": trade_id,
            "kind": "bond",
            "simulated": True,
        }
        return address, json.dumps(info, separators=(",", ":"))

    def allocate_multisig_trade_escrow(
        self, trade_id: str, seller_id: str, buyer_id: str
    ) -> tuple[str, str]:
        """
        Simulated 2-of-3 multisig escrow address (buyer + seller + coordinator).
        On-chain Monero multisig would use wallet RPC prepare/finalize_multisig; this fake
        path keeps funding and release tests deterministic.
        """
        next_index = len(self.confirmations_by_address) + 1
        address = f"45msig2of3{trade_id[:8]}{next_index}"
        self.confirmations_by_address.setdefault(address, 0)
        self.received_xmr_by_address.setdefault(address, 0.0)
        self.subaddress_index_by_address.setdefault(address, next_index)
        info = {
            "threshold": 2,
            "total": 3,
            "parties": ["seller", "buyer", "coordinator"],
            "seller_id_prefix": seller_id[:24],
            "buyer_id_prefix": (buyer_id or "")[:24],
            "trade_id": trade_id,
            "simulated": True,
        }
        return address, json.dumps(info, separators=(",", ":"))

    def get_confirmations(self, address: str) -> int:
        return self.confirmations_by_address.get(address, 0)

    def get_transfer_activity(self, address: str) -> TransferActivity:
        return TransferActivity(
            confirmations=self.get_confirmations(address),
            total_received_xmr=self.received_xmr_by_address.get(address, 0.0),
        )

    def get_subaddress_index(self, address: str) -> int | None:
        return self.subaddress_index_by_address.get(address)

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

    def release_multisig_escrow_to_buyer(
        self,
        deposit_subaddress: str,
        buyer_address: str,
        amount_xmr: float,
        trade_id: str,
    ) -> str:
        """Deprecated one-shot multisig simulation; use prepare/sign/submit API flow."""
        if not deposit_subaddress or not buyer_address or amount_xmr <= 0 or not trade_id:
            raise ValueError("invalid multisig escrow release parameters")
        if deposit_subaddress not in self.confirmations_by_address:
            raise ValueError("unknown multisig deposit address for fake wallet")
        return (
            f"fake-msig2of3-from-{deposit_subaddress[:16]}-"
            f"to-{buyer_address[:12]}-amt-{amount_xmr}-tid-{trade_id[:8]}"
        )

    def submit_multisig_release(
        self,
        deposit_subaddress: str,
        final_tx_data_hex: str,
        trade_id: str,
        buyer_address: str,
        amount_xmr: float,
    ) -> str:
        """
        Final broadcast step for fake multisig: validates placeholder chain and returns txid.
        """
        if not deposit_subaddress or not final_tx_data_hex or not trade_id:
            raise ValueError("invalid multisig submit parameters")
        if deposit_subaddress not in self.confirmations_by_address:
            raise ValueError("unknown multisig deposit address for fake wallet")
        if "::SIG(buyer)" not in final_tx_data_hex or "::SIG(seller)" not in final_tx_data_hex:
            raise ValueError("multisig tx is missing buyer or seller partial signatures")
        return (
            f"fake-msig2of3-submitted-from-{deposit_subaddress[:16]}-"
            f"to-{buyer_address[:12]}-amt-{amount_xmr}-tid-{trade_id[:8]}"
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
