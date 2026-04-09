from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
from typing import Protocol

from backend.trade_engine import Trade, TradeState


def _trade_from_row(row: tuple) -> Trade:
    """Map a full trades row (including Phase 3 bond columns) to a Trade."""
    maker_amt = row[19]
    taker_amt = row[20]
    return Trade(
        trade_id=row[0],
        state=TradeState(row[1]),
        amount_xmr=row[2],
        seller_id=row[3],
        buyer_id=row[4],
        deposit_address=row[5],
        buyer_payout_address=row[6],
        seller_refund_address=row[7],
        release_txid=row[8],
        refund_txid=row[9],
        dispute_reason=row[10],
        dispute_opened_at=datetime.fromisoformat(row[11]) if row[11] else None,
        required_confirmations=row[12],
        current_confirmations=row[13],
        funded_at=datetime.fromisoformat(row[14]) if row[14] else None,
        created_at=datetime.fromisoformat(row[15]),
        updated_at=datetime.fromisoformat(row[16]),
        maker_bond_address=row[17],
        taker_bond_address=row[18],
        maker_bond_amount=float(maker_amt) if maker_amt is not None else 0.01,
        taker_bond_amount=float(taker_amt) if taker_amt is not None else 0.01,
        maker_bond_confirmations=row[21] if row[21] is not None else 0,
        taker_bond_confirmations=row[22] if row[22] is not None else 0,
        deposit_subaddress_index=row[23],
        maker_bond_subaddress_index=row[24],
        taker_bond_subaddress_index=row[25],
    )


class TradeRepository(Protocol):
    def save(self, trade: Trade) -> Trade: ...

    def get(self, trade_id: str) -> Trade | None: ...

    def list_all(self) -> list[Trade]: ...

    def save_offer(self, offer: "Offer") -> "Offer": ...

    def get_offer(self, offer_id: str) -> "Offer | None": ...

    def list_active_offers(self) -> list["Offer"]: ...


@dataclass
class Offer:
    offer_id: str
    maker_id: str
    amount_xmr: float
    premium_pct: float
    fiat_currency: str
    payment_method: str
    maker_bond_amount: float = 0.01
    taker_bond_amount: float = 0.01
    is_active: bool = True
    taken_by: str | None = None
    trade_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


def _offer_from_row(row: tuple) -> Offer:
    return Offer(
        offer_id=row[0],
        maker_id=row[1],
        amount_xmr=row[2],
        premium_pct=row[3],
        fiat_currency=row[4],
        payment_method=row[5],
        maker_bond_amount=float(row[6]) if row[6] is not None else 0.01,
        taker_bond_amount=float(row[7]) if row[7] is not None else 0.01,
        is_active=bool(row[8]),
        taken_by=row[9],
        trade_id=row[10],
        created_at=datetime.fromisoformat(row[11]),
        updated_at=datetime.fromisoformat(row[12]),
    )


@dataclass
class InMemoryTradeRepository:
    _trades: dict[str, Trade] = field(default_factory=dict)
    _offers: dict[str, Offer] = field(default_factory=dict)

    def save(self, trade: Trade) -> Trade:
        self._trades[trade.trade_id] = trade
        return trade

    def get(self, trade_id: str) -> Trade | None:
        return self._trades.get(trade_id)

    def list_all(self) -> list[Trade]:
        return list(self._trades.values())

    def save_offer(self, offer: Offer) -> Offer:
        offer.updated_at = datetime.utcnow()
        self._offers[offer.offer_id] = offer
        return offer

    def get_offer(self, offer_id: str) -> Offer | None:
        return self._offers.get(offer_id)

    def list_active_offers(self) -> list[Offer]:
        return [o for o in self._offers.values() if o.is_active]


@dataclass
class SQLiteTradeRepository:
    db_path: str

    def __post_init__(self) -> None:
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # Allow watcher + sweeper + API to share SQLite with fewer transient locks.
        return sqlite3.connect(self.db_path, timeout=30)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    amount_xmr REAL NOT NULL,
                    seller_id TEXT NOT NULL,
                    buyer_id TEXT,
                    deposit_address TEXT,
                    buyer_payout_address TEXT,
                    seller_refund_address TEXT,
                    release_txid TEXT,
                    refund_txid TEXT,
                    dispute_reason TEXT,
                    dispute_opened_at TEXT,
                    required_confirmations INTEGER NOT NULL,
                    current_confirmations INTEGER NOT NULL,
                    funded_at TEXT,
                    maker_bond_address TEXT,
                    taker_bond_address TEXT,
                    maker_bond_amount REAL,
                    taker_bond_amount REAL,
                    maker_bond_confirmations INTEGER,
                    taker_bond_confirmations INTEGER,
                    deposit_subaddress_index INTEGER,
                    maker_bond_subaddress_index INTEGER,
                    taker_bond_subaddress_index INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS offers (
                    offer_id TEXT PRIMARY KEY,
                    maker_id TEXT NOT NULL,
                    amount_xmr REAL NOT NULL,
                    premium_pct REAL NOT NULL,
                    fiat_currency TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    maker_bond_amount REAL NOT NULL DEFAULT 0.01,
                    taker_bond_amount REAL NOT NULL DEFAULT 0.01,
                    is_active INTEGER NOT NULL,
                    taken_by TEXT,
                    trade_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            existing_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(trades)").fetchall()
            }
            wanted_cols = {
                "buyer_payout_address": "TEXT",
                "seller_refund_address": "TEXT",
                "release_txid": "TEXT",
                "refund_txid": "TEXT",
                "dispute_reason": "TEXT",
                "dispute_opened_at": "TEXT",
                "maker_bond_address": "TEXT",
                "taker_bond_address": "TEXT",
                "maker_bond_amount": "REAL",
                "taker_bond_amount": "REAL",
                "maker_bond_confirmations": "INTEGER",
                "taker_bond_confirmations": "INTEGER",
                "deposit_subaddress_index": "INTEGER",
                "maker_bond_subaddress_index": "INTEGER",
                "taker_bond_subaddress_index": "INTEGER",
            }
            for col, col_type in wanted_cols.items():
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")
            offer_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(offers)").fetchall()
            }
            wanted_offer_cols = {
                "maker_bond_amount": "REAL",
                "taker_bond_amount": "REAL",
            }
            for col, col_type in wanted_offer_cols.items():
                if col not in offer_cols:
                    conn.execute(f"ALTER TABLE offers ADD COLUMN {col} {col_type}")

    def save(self, trade: Trade) -> Trade:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trades (
                    trade_id, state, amount_xmr, seller_id, buyer_id,
                    deposit_address, buyer_payout_address, seller_refund_address,
                    release_txid, refund_txid, dispute_reason, dispute_opened_at,
                    required_confirmations, current_confirmations,
                    funded_at, created_at, updated_at,
                    maker_bond_address, taker_bond_address,
                    maker_bond_amount, taker_bond_amount,
                    maker_bond_confirmations, taker_bond_confirmations,
                    deposit_subaddress_index, maker_bond_subaddress_index, taker_bond_subaddress_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    state=excluded.state,
                    amount_xmr=excluded.amount_xmr,
                    seller_id=excluded.seller_id,
                    buyer_id=excluded.buyer_id,
                    deposit_address=excluded.deposit_address,
                    buyer_payout_address=excluded.buyer_payout_address,
                    seller_refund_address=excluded.seller_refund_address,
                    release_txid=excluded.release_txid,
                    refund_txid=excluded.refund_txid,
                    dispute_reason=excluded.dispute_reason,
                    dispute_opened_at=excluded.dispute_opened_at,
                    required_confirmations=excluded.required_confirmations,
                    current_confirmations=excluded.current_confirmations,
                    funded_at=excluded.funded_at,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    maker_bond_address=excluded.maker_bond_address,
                    taker_bond_address=excluded.taker_bond_address,
                    maker_bond_amount=excluded.maker_bond_amount,
                    taker_bond_amount=excluded.taker_bond_amount,
                    maker_bond_confirmations=excluded.maker_bond_confirmations,
                    taker_bond_confirmations=excluded.taker_bond_confirmations,
                    deposit_subaddress_index=excluded.deposit_subaddress_index,
                    maker_bond_subaddress_index=excluded.maker_bond_subaddress_index,
                    taker_bond_subaddress_index=excluded.taker_bond_subaddress_index
                """,
                (
                    trade.trade_id,
                    trade.state.value,
                    trade.amount_xmr,
                    trade.seller_id,
                    trade.buyer_id,
                    trade.deposit_address,
                    trade.buyer_payout_address,
                    trade.seller_refund_address,
                    trade.release_txid,
                    trade.refund_txid,
                    trade.dispute_reason,
                    trade.dispute_opened_at.isoformat() if trade.dispute_opened_at else None,
                    trade.required_confirmations,
                    trade.current_confirmations,
                    trade.funded_at.isoformat() if trade.funded_at else None,
                    trade.created_at.isoformat(),
                    trade.updated_at.isoformat(),
                    trade.maker_bond_address,
                    trade.taker_bond_address,
                    trade.maker_bond_amount,
                    trade.taker_bond_amount,
                    trade.maker_bond_confirmations,
                    trade.taker_bond_confirmations,
                    trade.deposit_subaddress_index,
                    trade.maker_bond_subaddress_index,
                    trade.taker_bond_subaddress_index,
                ),
            )
        return trade

    def get(self, trade_id: str) -> Trade | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    trade_id, state, amount_xmr, seller_id, buyer_id,
                    deposit_address, buyer_payout_address, seller_refund_address,
                    release_txid, refund_txid, dispute_reason, dispute_opened_at,
                    required_confirmations, current_confirmations,
                    funded_at, created_at, updated_at,
                    maker_bond_address, taker_bond_address,
                    maker_bond_amount, taker_bond_amount,
                    maker_bond_confirmations, taker_bond_confirmations,
                    deposit_subaddress_index, maker_bond_subaddress_index, taker_bond_subaddress_index
                FROM trades
                WHERE trade_id = ?
                """,
                (trade_id,),
            ).fetchone()

        if row is None:
            return None

        return _trade_from_row(row)

    def list_all(self) -> list[Trade]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    trade_id, state, amount_xmr, seller_id, buyer_id,
                    deposit_address, buyer_payout_address, seller_refund_address,
                    release_txid, refund_txid, dispute_reason, dispute_opened_at,
                    required_confirmations, current_confirmations,
                    funded_at, created_at, updated_at,
                    maker_bond_address, taker_bond_address,
                    maker_bond_amount, taker_bond_amount,
                    maker_bond_confirmations, taker_bond_confirmations,
                    deposit_subaddress_index, maker_bond_subaddress_index, taker_bond_subaddress_index
                FROM trades
                """
            ).fetchall()

        return [_trade_from_row(row) for row in rows]

    def add_audit_event(self, trade_id: str, actor_id: str, action: str, note: str | None) -> None:
        if not trade_id or not actor_id or not action:
            raise ValueError("trade_id, actor_id, and action are required")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (trade_id, actor_id, action, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (trade_id, actor_id, action, note, datetime.utcnow().isoformat()),
            )

    def save_offer(self, offer: Offer) -> Offer:
        offer.updated_at = datetime.utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO offers (
                    offer_id, maker_id, amount_xmr, premium_pct, fiat_currency, payment_method,
                    maker_bond_amount, taker_bond_amount, is_active, taken_by, trade_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(offer_id) DO UPDATE SET
                    maker_id=excluded.maker_id,
                    amount_xmr=excluded.amount_xmr,
                    premium_pct=excluded.premium_pct,
                    fiat_currency=excluded.fiat_currency,
                    payment_method=excluded.payment_method,
                    maker_bond_amount=excluded.maker_bond_amount,
                    taker_bond_amount=excluded.taker_bond_amount,
                    is_active=excluded.is_active,
                    taken_by=excluded.taken_by,
                    trade_id=excluded.trade_id,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    offer.offer_id,
                    offer.maker_id,
                    offer.amount_xmr,
                    offer.premium_pct,
                    offer.fiat_currency,
                    offer.payment_method,
                    offer.maker_bond_amount,
                    offer.taker_bond_amount,
                    1 if offer.is_active else 0,
                    offer.taken_by,
                    offer.trade_id,
                    offer.created_at.isoformat(),
                    offer.updated_at.isoformat(),
                ),
            )
        return offer

    def get_offer(self, offer_id: str) -> Offer | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    offer_id, maker_id, amount_xmr, premium_pct, fiat_currency, payment_method,
                    maker_bond_amount, taker_bond_amount,
                    is_active, taken_by, trade_id, created_at, updated_at
                FROM offers
                WHERE offer_id = ?
                """,
                (offer_id,),
            ).fetchone()
        if row is None:
            return None
        return _offer_from_row(row)

    def list_active_offers(self) -> list[Offer]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    offer_id, maker_id, amount_xmr, premium_pct, fiat_currency, payment_method,
                    maker_bond_amount, taker_bond_amount,
                    is_active, taken_by, trade_id, created_at, updated_at
                FROM offers
                WHERE is_active = 1
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [_offer_from_row(row) for row in rows]
