from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.repository import SQLiteTradeRepository
from backend.sweeper import run_stale_trade_sweep_loop


def main() -> None:
    logging.basicConfig(
        level=os.getenv("ROBOSATS_XMR_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    db_path = os.getenv("ROBOSATS_XMR_DB_PATH", "data/trades.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    repository = SQLiteTradeRepository(db_path=db_path)

    interval_seconds = float(
        os.getenv("ROBOSATS_XMR_SWEEPER_INTERVAL_SECONDS", "300")
    )
    run_stale_trade_sweep_loop(
        repository=repository,
        interval_seconds=interval_seconds,
        max_iterations=None,
    )


if __name__ == "__main__":
    main()
