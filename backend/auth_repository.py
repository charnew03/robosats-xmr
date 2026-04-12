from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
import secrets


@dataclass(frozen=True)
class PendingRegistration:
    setup_token: str
    passhash: str
    expires_at: datetime


class AuthRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=30)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_registrations (
                    setup_token TEXT PRIMARY KEY,
                    passhash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create_pending(self, *, setup_token: str, passhash: str, ttl_minutes: int = 60) -> None:
        now = datetime.utcnow()
        expires = now + timedelta(minutes=ttl_minutes)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pending_registrations (setup_token, passhash, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (setup_token, passhash, expires.isoformat(), now.isoformat()),
            )

    def get_pending(self, setup_token: str) -> PendingRegistration | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT setup_token, passhash, expires_at
                FROM pending_registrations
                WHERE setup_token = ?
                """,
                (setup_token,),
            ).fetchone()
        if row is None:
            return None
        return PendingRegistration(
            setup_token=row[0],
            passhash=row[1],
            expires_at=datetime.fromisoformat(row[2]),
        )

    def delete_pending(self, setup_token: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM pending_registrations WHERE setup_token = ?",
                (setup_token,),
            )

    def delete_expired_pending(self) -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM pending_registrations WHERE expires_at < ?",
                (now,),
            )
            return int(cur.rowcount or 0)

    def user_exists(self, user_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
        return row is not None

    def create_user(self, user_id: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (user_id, created_at) VALUES (?, ?)",
                (user_id, now),
            )

    def new_setup_token(self) -> str:
        return secrets.token_urlsafe(32)
