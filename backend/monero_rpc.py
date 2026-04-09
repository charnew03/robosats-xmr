from __future__ import annotations

from dataclasses import dataclass, field
import httpx

from backend.wallet_adapter import TransferActivity


@dataclass
class MoneroWalletRPC:
    base_url: str
    username: str
    password: str
    account_index: int = 0
    timeout_seconds: float = 10.0
    _subaddress_index_by_address: dict[str, int] = field(default_factory=dict)

    def _call(self, method: str, params: dict | None = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": method,
            "params": params or {},
        }
        response = httpx.post(
            f"{self.base_url}/json_rpc",
            json=payload,
            auth=(self.username, self.password),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"wallet rpc error: {body['error']}")
        return body.get("result", {})

    def get_version(self) -> str:
        result = self._call("get_version")
        version = result.get("version")
        return str(version) if version is not None else "unknown"

    def is_synced(self) -> bool:
        result = self._call("get_height")
        return bool(result.get("height", 0) > 0)

    def generate_subaddress(self, trade_id: str) -> str:
        result = self._call(
            "create_address",
            {"account_index": self.account_index, "label": f"trade:{trade_id}"},
        )
        address = result.get("address")
        if not address:
            raise RuntimeError("wallet rpc did not return address")
        maybe_index = result.get("address_index")
        if isinstance(maybe_index, int):
            self._subaddress_index_by_address[address] = maybe_index
        return address

    def get_subaddress_index(self, address: str) -> int | None:
        if address in self._subaddress_index_by_address:
            return self._subaddress_index_by_address[address]
        result = self._call("get_address", {"account_index": self.account_index})
        for entry in result.get("addresses", []):
            if entry.get("address") == address:
                idx = entry.get("address_index")
                if isinstance(idx, int):
                    self._subaddress_index_by_address[address] = idx
                    return idx
        return None

    def get_confirmations(self, address: str) -> int:
        return self.get_transfer_activity(address).confirmations

    def get_transfer_activity(self, address: str) -> TransferActivity:
        result = self._call(
            "get_transfers",
            {"in": True, "account_index": self.account_index},
        )
        incoming = [
            transfer
            for transfer in result.get("in", [])
            if transfer.get("address") == address
        ]
        if not incoming:
            return TransferActivity(confirmations=0, total_received_xmr=0.0)
        confirmations = max(int(transfer.get("confirmations", 0)) for transfer in incoming)
        atomic_total = sum(int(transfer.get("amount", 0)) for transfer in incoming)
        return TransferActivity(
            confirmations=confirmations,
            total_received_xmr=atomic_total / 1e12,
        )

    def send_xmr(self, address: str, amount_xmr: float) -> str:
        if not address:
            raise ValueError("address cannot be empty")
        if amount_xmr <= 0:
            raise ValueError("amount_xmr must be > 0")

        atomic_amount = int(amount_xmr * 1e12)
        result = self._call(
            "transfer",
            {
                "account_index": self.account_index,
                "destinations": [{"address": address, "amount": atomic_amount}],
            },
        )
        tx_hash = result.get("tx_hash")
        if not tx_hash:
            tx_hash_list = result.get("tx_hash_list")
            if isinstance(tx_hash_list, list) and tx_hash_list:
                tx_hash = tx_hash_list[0]
        if not tx_hash:
            raise RuntimeError("wallet rpc did not return tx hash")
        return str(tx_hash)

    def release_escrow_to_buyer(
        self, deposit_subaddress: str, buyer_address: str, amount_xmr: float
    ) -> str:
        """
        Transfer trade escrow to the buyer, preferring inputs from the deposit subaddress.

        Resolves subaddress indices from a prior incoming transfer to `deposit_subaddress`;
        if none is found, falls back to a normal transfer (wallet may use any unlocked outputs).
        """
        if not deposit_subaddress or not buyer_address:
            raise ValueError("deposit and buyer addresses are required")
        if amount_xmr <= 0:
            raise ValueError("amount_xmr must be > 0")

        subaddr_indices: list[list[int]] | None = None
        transfers = self._call(
            "get_transfers",
            {"in": True, "account_index": self.account_index},
        )
        incoming = transfers.get("in", [])
        for transfer in incoming:
            if transfer.get("address") != deposit_subaddress:
                continue
            idx = transfer.get("subaddr_index") or {}
            major = idx.get("major")
            minor = idx.get("minor")
            if major is not None and minor is not None:
                subaddr_indices = [[int(major), int(minor)]]
                break

        atomic_amount = int(amount_xmr * 1e12)
        params: dict = {
            "account_index": self.account_index,
            "destinations": [{"address": buyer_address, "amount": atomic_amount}],
        }
        if subaddr_indices:
            params["subaddr_indices"] = subaddr_indices

        result = self._call("transfer", params)
        tx_hash = result.get("tx_hash")
        if not tx_hash:
            tx_hash_list = result.get("tx_hash_list")
            if isinstance(tx_hash_list, list) and tx_hash_list:
                tx_hash = tx_hash_list[0]
        if not tx_hash:
            raise RuntimeError("wallet rpc did not return tx hash")
        return str(tx_hash)

    def release_bond(
        self, bond_subaddress: str, return_address: str, amount_xmr: float
    ) -> str:
        """
        Return a bond amount from bond subaddress back to owner return address.
        """
        return self.release_escrow_to_buyer(
            deposit_subaddress=bond_subaddress,
            buyer_address=return_address,
            amount_xmr=amount_xmr,
        )
