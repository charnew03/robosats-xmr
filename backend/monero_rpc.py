from __future__ import annotations

from dataclasses import dataclass
import httpx


@dataclass
class MoneroWalletRPC:
    base_url: str
    username: str
    password: str
    account_index: int = 0
    timeout_seconds: float = 10.0

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
        return address

    def get_confirmations(self, address: str) -> int:
        result = self._call(
            "get_transfers",
            {"in": True, "account_index": self.account_index},
        )
        incoming = result.get("in", [])
        if not incoming:
            return 0
        return max(
            (
                int(transfer.get("confirmations", 0))
                for transfer in incoming
                if transfer.get("address") == address
            ),
            default=0,
        )
