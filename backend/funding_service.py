from __future__ import annotations

from typing import Protocol

from backend.trade_engine import Trade


class WalletFundingRPC(Protocol):
    def generate_subaddress(self, trade_id: str) -> str: ...

    def get_confirmations(self, address: str) -> int: ...

    def send_xmr(self, address: str, amount_xmr: float) -> str: ...


def assign_trade_deposit(trade: Trade, wallet_rpc: WalletFundingRPC) -> str:
    address = wallet_rpc.generate_subaddress(trade.trade_id)
    trade.assign_deposit_address(address)
    return address


def refresh_trade_funding(trade: Trade, wallet_rpc: WalletFundingRPC) -> bool:
    if trade.deposit_address is None:
        raise ValueError("trade has no deposit address")

    confirmations = wallet_rpc.get_confirmations(trade.deposit_address)
    return trade.record_confirmations(confirmations)
