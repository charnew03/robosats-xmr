from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.fake_wallet import FakeWalletFundingRPC
from backend.monero_rpc import MoneroWalletRPC
from backend.repository import SQLiteTradeRepository
from backend.watcher import run_funding_refresh_loop


def main() -> None:
    logging.basicConfig(
        level=os.getenv("ROBOSATS_XMR_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    db_path = os.getenv("ROBOSATS_XMR_DB_PATH", "data/trades.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    repository = SQLiteTradeRepository(db_path=db_path)

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

    interval_seconds = float(os.getenv("ROBOSATS_XMR_WATCHER_INTERVAL_SECONDS", "10"))
    run_funding_refresh_loop(
        repository=repository,
        wallet_rpc=wallet_rpc,
        interval_seconds=interval_seconds,
        max_iterations=None,
    )


if __name__ == "__main__":
    main()
