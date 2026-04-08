from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.fake_wallet import FakeWalletFundingRPC
from backend.funding_service import assign_trade_deposit, refresh_trade_funding
from backend.monero_rpc import MoneroWalletRPC
from backend.repository import SQLiteTradeRepository, TradeRepository
from backend.risk_limits import RiskLimits, enforce_seller_open_trade_limit
from backend.rate_limit import RateLimiter
from backend.trade_engine import Trade, TradeState
from backend.wallet_adapter import release_escrow_to_buyer


logger = logging.getLogger(__name__)


class CreateTradeRequest(BaseModel):
    amount_xmr: float = Field(gt=0)
    seller_id: str = Field(min_length=1)
    buyer_id: str | None = None
    required_confirmations: int = Field(default=10, ge=1)


class SeedConfirmationsRequest(BaseModel):
    confirmations: int = Field(ge=0)


class ReleaseRequest(BaseModel):
    buyer_payout_address: str = Field(min_length=1)


class DisputeRequest(BaseModel):
    reason: str = Field(min_length=1)


class ModeratorResolveRequest(BaseModel):
    moderator_id: str = Field(min_length=1)
    outcome: str = Field(pattern="^(release|refund)$")
    address: str = Field(min_length=1)
    note: str | None = None


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
    buyer_payout_address: str | None = None
    seller_refund_address: str | None = None
    release_txid: str | None = None
    refund_txid: str | None = None
    dispute_reason: str | None = None
    dispute_opened_at: datetime | None = None


class HealthResponse(BaseModel):
    status: str
    db_path: str


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
        buyer_payout_address=trade.buyer_payout_address,
        seller_refund_address=trade.seller_refund_address,
        release_txid=trade.release_txid,
        refund_txid=trade.refund_txid,
        dispute_reason=trade.dispute_reason,
        dispute_opened_at=trade.dispute_opened_at,
    )


def create_app(
    *,
    db_path: str | None = None,
    use_fake_wallet: bool | None = None,
) -> FastAPI:
    app = FastAPI(title="robosats-xmr API")

    effective_db_path = db_path or os.getenv("ROBOSATS_XMR_DB_PATH", "data/trades.db")
    Path(effective_db_path).parent.mkdir(parents=True, exist_ok=True)
    trade_repository: TradeRepository = SQLiteTradeRepository(db_path=effective_db_path)

    rate_limiter = RateLimiter(
        max_requests=int(os.getenv("ROBOSATS_XMR_RL_MAX_REQUESTS", "60")),
        window_seconds=int(os.getenv("ROBOSATS_XMR_RL_WINDOW_SECONDS", "60")),
    )
    risk_limits = RiskLimits(
        max_open_trades_per_seller=int(
            os.getenv("ROBOSATS_XMR_MAX_OPEN_TRADES_PER_SELLER", "3")
        )
    )

    effective_use_fake_wallet = (
        use_fake_wallet
        if use_fake_wallet is not None
        else os.getenv("ROBOSATS_XMR_USE_FAKE_WALLET", "true").lower() == "true"
    )
    if effective_use_fake_wallet:
        wallet_rpc = FakeWalletFundingRPC()
    else:
        wallet_rpc = MoneroWalletRPC(
            base_url=os.getenv("MONERO_WALLET_RPC_URL", "http://127.0.0.1:18083"),
            username=os.getenv("MONERO_WALLET_RPC_USER", ""),
            password=os.getenv("MONERO_WALLET_RPC_PASSWORD", ""),
            account_index=int(os.getenv("MONERO_WALLET_ACCOUNT_INDEX", "0")),
        )

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.method}:{request.url.path}"
        if not rate_limiter.allow(key):
            return JSONResponse(
                status_code=429, content={"detail": "rate limit exceeded"}
            )
        return await call_next(request)

    @app.post("/trades", response_model=TradeResponse)
    def create_trade(payload: CreateTradeRequest) -> TradeResponse:
        try:
            enforce_seller_open_trade_limit(
                trade_repository, payload.seller_id, risk_limits
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    def seed_confirmations(
        trade_id: str, payload: SeedConfirmationsRequest
    ) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        if trade.deposit_address is None:
            raise HTTPException(status_code=400, detail="trade has no deposit address")
        if not isinstance(wallet_rpc, FakeWalletFundingRPC):
            raise HTTPException(
                status_code=400,
                detail="seed-confirmations is only available when using the fake wallet",
            )
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


    @app.post("/trades/{trade_id}/mark-fiat-paid", response_model=TradeResponse)
    def mark_fiat_paid(trade_id: str) -> TradeResponse:
        return _mark_fiat_paid(trade_id)

    # Phase 2 alias path kept explicit for settlement naming.
    @app.post("/trades/{trade_id}/release-escrow", response_model=TradeResponse)
    def release_escrow(trade_id: str, payload: ReleaseRequest) -> TradeResponse:
        return _release_escrow(trade_id, payload)

    @app.post("/trades/{trade_id}/release", response_model=TradeResponse)
    def release(trade_id: str, payload: ReleaseRequest) -> TradeResponse:
        return _release_escrow(trade_id, payload)

    # Phase 2 alias path kept explicit for dispute naming.
    @app.post("/trades/{trade_id}/open-dispute", response_model=TradeResponse)
    def open_dispute(trade_id: str, payload: DisputeRequest) -> TradeResponse:
        return _open_dispute(trade_id, payload)

    @app.post("/trades/{trade_id}/dispute", response_model=TradeResponse)
    def dispute(trade_id: str, payload: DisputeRequest) -> TradeResponse:
        return _open_dispute(trade_id, payload)

    def _mark_fiat_paid(trade_id: str) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        try:
            trade.mark_fiat_paid()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        trade_repository.save(trade)
        logger.info(
            "Phase2 mark-fiat-paid: trade=%s -> FIAT_MARKED_PAID",
            trade_id,
        )
        if hasattr(trade_repository, "add_audit_event"):
            trade_repository.add_audit_event(
                trade_id, trade.buyer_id or "buyer", "fiat_marked_paid", None
            )
        return to_trade_response(trade)

    def _release_escrow(trade_id: str, payload: ReleaseRequest) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        # Seller settlement path only; DISPUTED trades stay frozen here (moderator uses
        # a separate resolve endpoint that may call set_release).
        if trade.state != TradeState.FIAT_MARKED_PAID:
            raise HTTPException(
                status_code=400,
                detail="trade must be FIAT_MARKED_PAID to release escrow",
            )
        if trade.deposit_address is None:
            raise HTTPException(
                status_code=400, detail="trade has no deposit address for escrow release"
            )
        try:
            # Wallet sends the exact trade notional toward the buyer; fake wallet simulates
            # from the deposit subaddress; real RPC prefers subaddr_indices when known.
            txid = release_escrow_to_buyer(
                wallet_rpc,
                trade.deposit_address,
                payload.buyer_payout_address,
                trade.amount_xmr,
            )
            trade.set_release(payload.buyer_payout_address, txid)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502, detail=f"wallet release failed: {exc}"
            ) from exc
        trade_repository.save(trade)
        logger.info(
            "Phase2 release-escrow: trade=%s txid=%s -> RELEASED",
            trade_id,
            txid,
        )
        if hasattr(trade_repository, "add_audit_event"):
            trade_repository.add_audit_event(
                trade_id, trade.seller_id, "release_escrow", txid
            )
        return to_trade_response(trade)

    def _open_dispute(trade_id: str, payload: DisputeRequest) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        try:
            trade.open_dispute(payload.reason)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        trade_repository.save(trade)
        logger.info(
            "Phase2 open-dispute: trade=%s reason=%r -> DISPUTED (settlement frozen)",
            trade_id,
            payload.reason[:80] if payload.reason else "",
        )
        if hasattr(trade_repository, "add_audit_event"):
            trade_repository.add_audit_event(
                trade_id, trade.seller_id, "dispute_opened", payload.reason
            )
        return to_trade_response(trade)

    @app.post("/trades/{trade_id}/moderator/resolve", response_model=TradeResponse)
    def moderator_resolve(
        trade_id: str, payload: ModeratorResolveRequest
    ) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        try:
            if trade.state != TradeState.DISPUTED:
                raise ValueError("trade must be DISPUTED to resolve")
            txid = wallet_rpc.send_xmr(payload.address, trade.amount_xmr)
            if payload.outcome == "release":
                trade.set_release(payload.address, txid)
                action = "moderator_release"
            else:
                trade.set_refund(payload.address, txid)
                action = "moderator_refund"
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        trade_repository.save(trade)
        if hasattr(trade_repository, "add_audit_event"):
            trade_repository.add_audit_event(
                trade_id, payload.moderator_id, action, payload.note or txid
            )
        return to_trade_response(trade)

    @app.get("/trades/{trade_id}", response_model=TradeResponse)
    def get_trade(trade_id: str) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        return to_trade_response(trade)

    @app.get("/trades", response_model=list[TradeResponse])
    def list_trades() -> list[TradeResponse]:
        trades = trade_repository.list_all()
        return [to_trade_response(trade) for trade in trades]


    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", db_path=effective_db_path)

    return app


app = create_app()
