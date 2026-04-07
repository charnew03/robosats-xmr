from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.funding_service import assign_trade_deposit, refresh_trade_funding
from backend.monero_rpc import MoneroWalletRPC
from backend.repository import SQLiteTradeRepository, TradeRepository
from backend.trade_engine import Trade


class CreateTradeRequest(BaseModel):
    amount_xmr: float = Field(gt=0)
    seller_id: str = Field(min_length=1)
    buyer_id: str | None = None
    required_confirmations: int = Field(default=10, ge=1)


class SeedConfirmationsRequest(BaseModel):
    confirmations: int = Field(ge=0)


class TradeResponse(BaseModel):
    trade_id: str
    state: str
    amount_xmr: float
    seller_id: str
    buyer_id: str | None
    deposit_address: str | None
    required_confirmations: int
    current_confirmations: int
    funded_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    db_path: str


class FakeWalletFundingRPC:
    def __init__(self) -> None:
        self.confirmations_by_address: dict[str, int] = {}

    def generate_subaddress(self, trade_id: str) -> str:
        address = f"48xmr{trade_id[:8]}{len(self.confirmations_by_address) + 1}"
        self.confirmations_by_address.setdefault(address, 0)
        return address

    def get_confirmations(self, address: str) -> int:
        return self.confirmations_by_address.get(address, 0)


def to_trade_response(trade: Trade) -> TradeResponse:
    return TradeResponse(
        trade_id=trade.trade_id,
        state=trade.state.value,
        amount_xmr=trade.amount_xmr,
        seller_id=trade.seller_id,
        buyer_id=trade.buyer_id,
        deposit_address=trade.deposit_address,
        required_confirmations=trade.required_confirmations,
        current_confirmations=trade.current_confirmations,
        funded_at=trade.funded_at,
    )


app = FastAPI(title="robosats-xmr API")
db_path = os.getenv("ROBOSATS_XMR_DB_PATH", "data/trades.db")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)
trade_repository: TradeRepository = SQLiteTradeRepository(db_path=db_path)
use_fake_wallet = os.getenv("ROBOSATS_XMR_USE_FAKE_WALLET", "true").lower() == "true"
if use_fake_wallet:
    wallet_rpc = FakeWalletFundingRPC()
else:
    wallet_rpc = MoneroWalletRPC(
        base_url=os.getenv("MONERO_WALLET_RPC_URL", "http://127.0.0.1:18083"),
        username=os.getenv("MONERO_WALLET_RPC_USER", ""),
        password=os.getenv("MONERO_WALLET_RPC_PASSWORD", ""),
        account_index=int(os.getenv("MONERO_WALLET_ACCOUNT_INDEX", "0")),
    )


@app.post("/trades", response_model=TradeResponse)
def create_trade(payload: CreateTradeRequest) -> TradeResponse:
    trade = Trade(
        trade_id=str(uuid4()),
        amount_xmr=payload.amount_xmr,
        seller_id=payload.seller_id,
        buyer_id=payload.buyer_id,
        required_confirmations=payload.required_confirmations,
    )
    trade_repository.save(trade)
    return to_trade_response(trade)


@app.post("/trades/{trade_id}/assign-deposit", response_model=TradeResponse)
def assign_deposit(trade_id: str) -> TradeResponse:
    trade = trade_repository.get(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="trade not found")
    assign_trade_deposit(trade, wallet_rpc)
    trade_repository.save(trade)
    return to_trade_response(trade)


@app.post("/trades/{trade_id}/seed-confirmations", response_model=TradeResponse)
def seed_confirmations(trade_id: str, payload: SeedConfirmationsRequest) -> TradeResponse:
    trade = trade_repository.get(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="trade not found")
    if trade.deposit_address is None:
        raise HTTPException(status_code=400, detail="trade has no deposit address")
    wallet_rpc.confirmations_by_address[trade.deposit_address] = payload.confirmations
    return to_trade_response(trade)


@app.post("/trades/{trade_id}/refresh-funding", response_model=TradeResponse)
def refresh_funding(trade_id: str) -> TradeResponse:
    trade = trade_repository.get(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="trade not found")
    try:
        refresh_trade_funding(trade, wallet_rpc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    trade_repository.save(trade)
    return to_trade_response(trade)


@app.get("/trades/{trade_id}", response_model=TradeResponse)
def get_trade(trade_id: str) -> TradeResponse:
    trade = trade_repository.get(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="trade not found")
    return to_trade_response(trade)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", db_path=db_path)
