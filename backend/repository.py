from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
from typing import Protocol

from backend.trade_engine import Trade, TradeState


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
        return sqlite3.connect(self.db_path)

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
                    required_confirmations INTEGER NOT NULL,
                    current_confirmations INTEGER NOT NULL,
                    funded_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save(self, trade: Trade) -> Trade:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trades (
                    trade_id, state, amount_xmr, seller_id, buyer_id,
                    deposit_address, required_confirmations, current_confirmations,
                    funded_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    state=excluded.state,
                    amount_xmr=excluded.amount_xmr,
                    seller_id=excluded.seller_id,
                    buyer_id=excluded.buyer_id,
                    deposit_address=excluded.deposit_address,
                    required_confirmations=excluded.required_confirmations,
                    current_confirmations=excluded.current_confirmations,
                    funded_at=excluded.funded_at,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    trade.trade_id,
                    trade.state.value,
                    trade.amount_xmr,
                    trade.seller_id,
                    trade.buyer_id,
                    trade.deposit_address,
                    trade.required_confirmations,
                    trade.current_confirmations,
                    trade.funded_at.isoformat() if trade.funded_at else None,
                    trade.created_at.isoformat(),
                    trade.updated_at.isoformat(),
                ),
            )
        return trade

    def get(self, trade_id: str) -> Trade | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    trade_id, state, amount_xmr, seller_id, buyer_id,
                    deposit_address, required_confirmations, current_confirmations,
                    funded_at, created_at, updated_at
                FROM trades
                WHERE trade_id = ?
                """,
                (trade_id,),
            ).fetchone()

        if row is None:
            return None

        return Trade(
            trade_id=row[0],
            state=TradeState(row[1]),
            amount_xmr=row[2],
            seller_id=row[3],
            buyer_id=row[4],
            deposit_address=row[5],
            required_confirmations=row[6],
            current_confirmations=row[7],
            funded_at=datetime.fromisoformat(row[8]) if row[8] else None,
            created_at=datetime.fromisoformat(row[9]),
            updated_at=datetime.fromisoformat(row[10]),
        )

    def list_all(self) -> list[Trade]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    trade_id, state, amount_xmr, seller_id, buyer_id,
                    deposit_address, required_confirmations, current_confirmations,
                    funded_at, created_at, updated_at
                FROM trades
                """
            ).fetchall()

        return [
            Trade(
                trade_id=row[0],
                state=TradeState(row[1]),
                amount_xmr=row[2],
                seller_id=row[3],
                buyer_id=row[4],
                deposit_address=row[5],
                required_confirmations=row[6],
                current_confirmations=row[7],
                funded_at=datetime.fromisoformat(row[8]) if row[8] else None,
                created_at=datetime.fromisoformat(row[9]),
                updated_at=datetime.fromisoformat(row[10]),
            )
            for row in rows
        ]
