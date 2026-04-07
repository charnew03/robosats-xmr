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
