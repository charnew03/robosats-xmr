from pathlib import Path

from backend.repository import SQLiteTradeRepository
from backend.trade_engine import Trade, TradeState


def test_sqlite_repository_persists_trade_between_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "trades.db"
    repo_one = SQLiteTradeRepository(db_path=str(db_path))

    trade = Trade(trade_id="persist-1", amount_xmr=0.33, seller_id="seller-persist")
    trade.assign_deposit_address("48xmrPersistAddr")
    trade.record_confirmations(10)
    repo_one.save(trade)

    repo_two = SQLiteTradeRepository(db_path=str(db_path))
    loaded = repo_two.get("persist-1")

    assert loaded is not None
    assert loaded.trade_id == "persist-1"
    assert loaded.state == TradeState.FUNDED
    assert loaded.current_confirmations == 10
    assert loaded.deposit_address == "48xmrPersistAddr"


def test_sqlite_repository_persists_release_and_dispute_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "trades2.db"
    repo_one = SQLiteTradeRepository(db_path=str(db_path))

    trade = Trade(trade_id="persist-2", amount_xmr=0.44, seller_id="seller-persist-2")
    trade.assign_deposit_address("48xmrPersistAddr2")
    trade.record_confirmations(10)
    trade.mark_fiat_paid()
    trade.open_dispute("testing dispute persistence")
    trade.set_refund("48xmrRefundAddr", "txid-123")
    repo_one.save(trade)

    repo_two = SQLiteTradeRepository(db_path=str(db_path))
    loaded = repo_two.get("persist-2")

    assert loaded is not None
    assert loaded.dispute_reason == "testing dispute persistence"
    assert loaded.refund_txid == "txid-123"
    assert loaded.seller_refund_address == "48xmrRefundAddr"
