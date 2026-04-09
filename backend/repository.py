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
    )


class TradeRepository(Protocol):
    def save(self, trade: Trade) -> Trade: ...

    def get(self, trade_id: str) -> Trade | None: ...

    def list_all(self) -> list[Trade]: ...


@dataclass
class InMemoryTradeRepository:
    _trades: dict[str, Trade] = field(default_factory=dict)

    def save(self, trade: Trade) -> Trade:
        self._trades[trade.trade_id] = trade
        return trade

    def get(self, trade_id: str) -> Trade | None:
        return self._trades.get(trade_id)

    def list_all(self) -> list[Trade]:
        return list(self._trades.values())


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
            }
            for col, col_type in wanted_cols.items():
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")

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
                    maker_bond_amount, taker_bond_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    taker_bond_amount=excluded.taker_bond_amount
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
                    maker_bond_amount, taker_bond_amount
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
                    maker_bond_amount, taker_bond_amount
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
