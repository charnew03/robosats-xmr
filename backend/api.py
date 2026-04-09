from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.bond_service import assign_trade_bonds
from backend.fake_wallet import FakeWalletFundingRPC
from backend.funding_service import assign_trade_deposit, refresh_trade_funding
from backend.monero_rpc import MoneroWalletRPC
from backend.repository import Offer, SQLiteTradeRepository, TradeRepository
from backend.risk_limits import RiskLimits, enforce_seller_open_trade_limit
from backend.rate_limit import RateLimiter
from backend.trade_engine import Trade, TradeState
from backend.wallet_adapter import (
    reconcile_address_activity,
    release_bond_to_owner,
    release_escrow_to_buyer,
    resolve_subaddress_index,
)


logger = logging.getLogger(__name__)


class CreateTradeRequest(BaseModel):
    amount_xmr: float = Field(gt=0)
    seller_id: str = Field(min_length=1)
    buyer_id: str | None = None
    required_confirmations: int = Field(default=10, ge=1)
    # Phase 3: bond notionals (custodial); addresses generated at assign-deposit.
    maker_bond_amount_xmr: float = Field(default=0.01, gt=0)
    taker_bond_amount_xmr: float = Field(default=0.01, gt=0)


class SeedConfirmationsRequest(BaseModel):
    confirmations: int = Field(ge=0)


class ReleaseRequest(BaseModel):
    buyer_payout_address: str = Field(min_length=1)
    maker_return_address: str | None = None
    taker_return_address: str | None = None


class DisputeRequest(BaseModel):
    reason: str = Field(min_length=1)


class CollaborativeCancelRequest(BaseModel):
    """Phase 3: mutual cancel before trade is funded (CREATED or FUNDS_PENDING only)."""

    actor_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    maker_return_address: str | None = None
    taker_return_address: str | None = None


class CreateOfferRequest(BaseModel):
    maker_id: str = Field(min_length=1)
    amount_xmr: float = Field(gt=0)
    premium_pct: float = Field(default=0.0)
    fiat_currency: str = Field(min_length=2)
    payment_method: str = Field(min_length=1)
    maker_bond_amount_xmr: float = Field(default=0.01, gt=0)
    taker_bond_amount_xmr: float = Field(default=0.01, gt=0)


class TakeOfferRequest(BaseModel):
    taker_id: str = Field(min_length=1)
    required_confirmations: int = Field(default=10, ge=1)


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
    maker_bond_address: str | None = None
    taker_bond_address: str | None = None
    maker_bond_amount: float = 0.01
    taker_bond_amount: float = 0.01
    maker_bond_confirmations: int = 0
    taker_bond_confirmations: int = 0
    deposit_subaddress_index: int | None = None
    maker_bond_subaddress_index: int | None = None
    taker_bond_subaddress_index: int | None = None


class OfferResponse(BaseModel):
    offer_id: str
    maker_id: str
    amount_xmr: float
    premium_pct: float
    fiat_currency: str
    payment_method: str
    maker_bond_amount: float
    taker_bond_amount: float
    is_active: bool
    taken_by: str | None
    trade_id: str | None
    created_at: datetime
    updated_at: datetime


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
        maker_bond_address=trade.maker_bond_address,
        taker_bond_address=trade.taker_bond_address,
        maker_bond_amount=trade.maker_bond_amount,
        taker_bond_amount=trade.taker_bond_amount,
        maker_bond_confirmations=trade.maker_bond_confirmations,
        taker_bond_confirmations=trade.taker_bond_confirmations,
        deposit_subaddress_index=trade.deposit_subaddress_index,
        maker_bond_subaddress_index=trade.maker_bond_subaddress_index,
        taker_bond_subaddress_index=trade.taker_bond_subaddress_index,
    )


def to_offer_response(offer: Offer) -> OfferResponse:
    return OfferResponse(
        offer_id=offer.offer_id,
        maker_id=offer.maker_id,
        amount_xmr=offer.amount_xmr,
        premium_pct=offer.premium_pct,
        fiat_currency=offer.fiat_currency,
        payment_method=offer.payment_method,
        maker_bond_amount=offer.maker_bond_amount,
        taker_bond_amount=offer.taker_bond_amount,
        is_active=offer.is_active,
        taken_by=offer.taken_by,
        trade_id=offer.trade_id,
        created_at=offer.created_at,
        updated_at=offer.updated_at,
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
            maker_bond_amount=payload.maker_bond_amount_xmr,
            taker_bond_amount=payload.taker_bond_amount_xmr,
        )
        trade_repository.save(trade)
        return to_trade_response(trade)

    @app.post("/offers", response_model=OfferResponse)
    def create_offer(payload: CreateOfferRequest) -> OfferResponse:
        try:
            enforce_seller_open_trade_limit(
                trade_repository, payload.maker_id, risk_limits
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        offer = Offer(
            offer_id=str(uuid4()),
            maker_id=payload.maker_id,
            amount_xmr=payload.amount_xmr,
            premium_pct=payload.premium_pct,
            fiat_currency=payload.fiat_currency.upper(),
            payment_method=payload.payment_method,
            maker_bond_amount=payload.maker_bond_amount_xmr,
            taker_bond_amount=payload.taker_bond_amount_xmr,
        )
        trade_repository.save_offer(offer)
        return to_offer_response(offer)

    @app.get("/offers", response_model=list[OfferResponse])
    def list_offers() -> list[OfferResponse]:
        offers = trade_repository.list_active_offers()
        return [to_offer_response(offer) for offer in offers]

    @app.post("/offers/{offer_id}/take", response_model=TradeResponse)
    def take_offer(offer_id: str, payload: TakeOfferRequest) -> TradeResponse:
        offer = trade_repository.get_offer(offer_id)
        if offer is None:
            raise HTTPException(status_code=404, detail="offer not found")
        if not offer.is_active:
            raise HTTPException(status_code=400, detail="offer is not active")
        try:
            enforce_seller_open_trade_limit(
                trade_repository, offer.maker_id, risk_limits
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        # Offer-to-trade conversion: taker accepts posted maker offer and we immediately
        # instantiate a real trade in FUNDS_PENDING with inherited bond config.
        trade = Trade(
            trade_id=str(uuid4()),
            amount_xmr=offer.amount_xmr,
            seller_id=offer.maker_id,
            buyer_id=payload.taker_id,
            required_confirmations=payload.required_confirmations,
            maker_bond_amount=offer.maker_bond_amount,
            taker_bond_amount=offer.taker_bond_amount,
        )
        assign_trade_deposit(trade, wallet_rpc)
        assign_trade_bonds(trade, wallet_rpc)
        trade.deposit_subaddress_index = resolve_subaddress_index(
            wallet_rpc, trade.deposit_address
        )
        trade.maker_bond_subaddress_index = resolve_subaddress_index(
            wallet_rpc, trade.maker_bond_address
        )
        trade.taker_bond_subaddress_index = resolve_subaddress_index(
            wallet_rpc, trade.taker_bond_address
        )

        trade_repository.save(trade)
        offer.is_active = False
        offer.taken_by = payload.taker_id
        offer.trade_id = trade.trade_id
        trade_repository.save_offer(offer)
        if hasattr(trade_repository, "add_audit_event"):
            trade_repository.add_audit_event(
                trade.trade_id,
                payload.taker_id,
                "offer_taken",
                f"offer_id={offer.offer_id}",
            )
        return to_trade_response(trade)


    @app.post("/trades/{trade_id}/assign-deposit", response_model=TradeResponse)
    def assign_deposit(trade_id: str) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        assign_trade_deposit(trade, wallet_rpc)
        # Phase 3: separate subaddresses for maker (seller) and taker (buyer) bonds.
        assign_trade_bonds(trade, wallet_rpc)
        trade.deposit_subaddress_index = resolve_subaddress_index(
            wallet_rpc, trade.deposit_address
        )
        trade.maker_bond_subaddress_index = resolve_subaddress_index(
            wallet_rpc, trade.maker_bond_address
        )
        trade.taker_bond_subaddress_index = resolve_subaddress_index(
            wallet_rpc, trade.taker_bond_address
        )
        trade_repository.save(trade)
        logger.info(
            "Phase3 bonds assigned: trade=%s maker_addr=%s taker_addr=%s",
            trade_id,
            (trade.maker_bond_address or "")[:20],
            (trade.taker_bond_address or "")[:20],
        )
        if hasattr(trade_repository, "add_audit_event"):
            trade_repository.add_audit_event(
                trade_id,
                trade.seller_id,
                "bonds_assigned",
                f"maker_bond={trade.maker_bond_amount} taker_bond={trade.taker_bond_amount}",
            )
        return to_trade_response(trade)


    @app.post("/trades/{trade_id}/cancel", response_model=TradeResponse)
    def collaborative_cancel(
        trade_id: str, payload: CollaborativeCancelRequest
    ) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        if trade.state not in (TradeState.CREATED, TradeState.FUNDS_PENDING):
            raise HTTPException(
                status_code=400,
                detail="collaborative cancel only allowed before trade is FUNDED",
            )
        bond_notes: list[str] = []
        # Phase 3: optional bond return flow. If return addresses are supplied and
        # bond subaddresses are already allocated, return bond notionals before cancel.
        try:
            if payload.maker_return_address and trade.maker_bond_address:
                maker_txid = release_bond_to_owner(
                    wallet_rpc,
                    trade.maker_bond_address,
                    payload.maker_return_address,
                    trade.maker_bond_amount,
                )
                bond_notes.append(f"maker_bond_returned:{maker_txid}")
            if payload.taker_return_address and trade.taker_bond_address:
                taker_txid = release_bond_to_owner(
                    wallet_rpc,
                    trade.taker_bond_address,
                    payload.taker_return_address,
                    trade.taker_bond_amount,
                )
                bond_notes.append(f"taker_bond_returned:{taker_txid}")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502, detail=f"wallet bond return failed: {exc}"
            ) from exc
        try:
            trade.cancel(f"collaborative: {payload.reason}")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        trade_repository.save(trade)
        logger.info(
            "Phase3 collaborative cancel: trade=%s actor=%s",
            trade_id,
            payload.actor_id,
        )
        if hasattr(trade_repository, "add_audit_event"):
            trade_repository.add_audit_event(
                trade_id,
                payload.actor_id,
                "collaborative_cancel",
                "; ".join([payload.reason, *bond_notes]) if bond_notes else payload.reason,
            )
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
            _refresh_bond_confirmations(trade)
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
        if trade.state in (TradeState.RELEASED, TradeState.DISPUTED):
            raise HTTPException(
                status_code=400,
                detail="trade is RELEASED or DISPUTED; no further settlement actions",
            )
        try:
            _ensure_bonds_accounted_for(trade)
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
        if trade.state in (TradeState.RELEASED, TradeState.DISPUTED):
            raise HTTPException(
                status_code=400,
                detail="trade is RELEASED or DISPUTED; no further settlement actions",
            )
        # Seller settlement path only; must be FIAT_MARKED_PAID.
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
            _ensure_bonds_accounted_for(trade)
            # Wallet sends the exact trade notional toward the buyer; fake wallet simulates
            # from the deposit subaddress; real RPC prefers subaddr_indices when known.
            txid = release_escrow_to_buyer(
                wallet_rpc,
                trade.deposit_address,
                payload.buyer_payout_address,
                trade.amount_xmr,
            )
            trade.set_release(payload.buyer_payout_address, txid)
            bond_returns: list[str] = []
            if payload.maker_return_address and trade.maker_bond_address:
                maker_txid = release_bond_to_owner(
                    wallet_rpc,
                    trade.maker_bond_address,
                    payload.maker_return_address,
                    trade.maker_bond_amount,
                )
                bond_returns.append(f"maker:{maker_txid}")
            if payload.taker_return_address and trade.taker_bond_address:
                taker_txid = release_bond_to_owner(
                    wallet_rpc,
                    trade.taker_bond_address,
                    payload.taker_return_address,
                    trade.taker_bond_amount,
                )
                bond_returns.append(f"taker:{taker_txid}")
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
                trade_id,
                trade.seller_id,
                "release_escrow",
                "; ".join([txid, *bond_returns]) if bond_returns else txid,
            )
        return to_trade_response(trade)

    def _open_dispute(trade_id: str, payload: DisputeRequest) -> TradeResponse:
        trade = trade_repository.get(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="trade not found")
        if trade.state == TradeState.RELEASED:
            raise HTTPException(
                status_code=400,
                detail="trade is RELEASED; no further settlement actions",
            )
        if trade.state == TradeState.DISPUTED:
            raise HTTPException(
                status_code=400,
                detail="trade is already DISPUTED",
            )
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
            trade_repository.add_audit_event(
                trade_id,
                "coordinator",
                "bond_slash_placeholder",
                "disputed trade: bonds retained by coordinator (placeholder)",
            )
        logger.info(
            "Phase3 bond slash placeholder: trade=%s bonds retained on dispute",
            trade_id,
        )
        return to_trade_response(trade)

    def _ensure_bonds_accounted_for(trade: Trade) -> None:
        # Basic Phase 3 guard: settlement actions require bond amounts and
        # subaddresses to be present, proving bond accounting has been configured.
        if trade.maker_bond_amount <= 0 or trade.taker_bond_amount <= 0:
            raise ValueError("maker/taker bond amounts must be configured before settlement")
        if not trade.maker_bond_address or not trade.taker_bond_address:
            raise ValueError(
                "maker/taker bond subaddresses must be assigned before settlement"
            )
        if (
            trade.maker_bond_subaddress_index is None
            or trade.taker_bond_subaddress_index is None
            or trade.deposit_subaddress_index is None
        ):
            raise ValueError("bond/deposit subaddress indexes must be resolved")

    def _refresh_bond_confirmations(trade: Trade) -> None:
        if trade.maker_bond_address:
            maker_activity = reconcile_address_activity(wallet_rpc, trade.maker_bond_address)
            trade.maker_bond_confirmations = maker_activity.confirmations
        if trade.taker_bond_address:
            taker_activity = reconcile_address_activity(wallet_rpc, trade.taker_bond_address)
            trade.taker_bond_confirmations = taker_activity.confirmations

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
