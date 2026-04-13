# robosats-xmr

**Monero-native RoboSats-style P2P trading:** fiat ↔ XMR with **2-of-3 multisig escrow by default** (coordinator + buyer + seller), **10-block funding finality**, and a **non-custodial release path** where the buyer and seller contribute partial signatures; the coordinator prepares the unsigned transaction and submits only the fully signed result.

## Phases

| Phase | Scope | Status |
|------:|-------|--------|
| 1 | Trades, deposits, funding refresh, watcher | Done |
| 2 | Settlement, disputes, release | Done |
| 3 | Bonds, risk limits, sweeper, collaborative cancel | Done |
| 4 | Order book (`POST/GET /offers`, take → trade) | Done |
| MVP | Vite frontend: book, auth, create offer, dashboard, trade detail + chat | Done |
| Multisig | Prepare / sign / submit release API + wallet-rpc hooks | Done |

Evidence and checklists: `docs/TESTING.md`.

## Current capabilities

### Backend

- Trade lifecycle through **FUNDS_PENDING** → **FUNDED** (default 10 confirmations) → **FIAT_MARKED_PAID** → **RELEASED**, plus disputes and collaborative cancel before funding finalizes.
- **Default 2-of-3 multisig product mode** for escrow and bond receive addresses (`ROBOSATS_XMR_ESCROW_MODE` unset or `multisig_2of3`). **Legacy** single coordinator subaddress per trade: set `ROBOSATS_XMR_ESCROW_MODE=legacy` (or `custodial` / `subaddress` / `single`).
- **Non-custodial escrow release:** `POST /trades/{id}/release-escrow/prepare` (unsigned `multisig_txset`), `.../sign` (buyer then seller, with optional pasted `tx_data_hex` from each party’s wallet), `.../submit` (coordinator `submit_multisig` + `release_txid`). Legacy trades still use one-shot `POST .../release-escrow`.
- Order book, maker/taker bonds, SQLite persistence, optional **Tor** hidden service for the API, seed-based accounts + JWT (`docs/` + code).
- **`GET /status`:** database path, wallet mode (`fake` vs `real`), escrow mode, RPC reachability, whether the coordinator `wallet-rpc` wallet reports **multisig**, and whether multisig release is RPC-ready.

### Frontend

- Order book, register/login (25-word seed), create offer, dashboard, trade detail.
- Trade chat (local browser storage MVP): **parties exchange standard Monero addresses here**; no wallet connect or seed import in the UI.
- Trade detail: **Copy trade ID**, **Copy deposit address**, multisig release wizard (prepare → buyer sign → seller sign → submit), clearer loading/error toasts for key actions.

### Docker / Tor

- `docker compose` stack with **stagenet** `monerod` + `monero-wallet-rpc` (see compose files).
- Optional **Tor** service exposing the API as an onion service (see compose + comments below).

## How to run

1. **Install** Python 3.11+ and `python -m pip install -r requirements-dev.txt` from the repo root.
2. **API:** `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000` — OpenAPI at `http://127.0.0.1:8000/docs`. **`GET /status`** summarizes wallet and multisig readiness.
3. **Funding watcher** (recommended whenever trades use on-chain confirmations): set `ROBOSATS_XMR_DB_PATH` and the same wallet RPC variables as the API (`MONERO_WALLET_RPC_URL`, credentials, account index), then `python -m backend.watcher_main` (interval `ROBOSATS_XMR_WATCHER_INTERVAL_SECONDS`, default `10`).
4. **Stale-trade sweeper:** same `ROBOSATS_XMR_DB_PATH`, then `python -m backend.sweeper_main` (interval `ROBOSATS_XMR_SWEEPER_INTERVAL_SECONDS`, default `300`).
5. **Frontend:** `cd frontend && npm install && npm run dev -- --host 127.0.0.1` (configure `VITE_API_BASE_URL` in `frontend/.env` if the API is not on `http://127.0.0.1:8000`).

Optional demo listings (with the API running): `python scripts/seed_demo_offers.py`.

## Stagenet (Docker)

Compose files bundle **stagenet** daemons and optional coordinator **wallet-rpc**. Use a public stagenet faucet for test XMR.

**Docker caveat:** volume permissions, port conflicts, or image pulls can fail on some hosts. If `docker compose up` misbehaves, run the stack **manually**:

1. Start **monerod** (stagenet) and **monero-wallet-rpc** with the same network and RPC ports you configure in the API (see Monero docs for stagenet flags).
2. Set `ROBOSATS_XMR_USE_FAKE_WALLET=false`, `MONERO_WALLET_RPC_URL`, `MONERO_WALLET_RPC_USER`, `MONERO_WALLET_RPC_PASSWORD`, and `ROBOSATS_XMR_DB_PATH` to point at your live wallet and shared SQLite file.
3. Run **`uvicorn backend.main:app`** on the host (or in a venv), then **`python -m backend.watcher_main`** and optionally **`python -m backend.sweeper_main`** in separate terminals with the **same** `ROBOSATS_XMR_DB_PATH`.

For **non-custodial multisig release** on stagenet, the coordinator `wallet-rpc` must open a **2-of-3 multisig** wallet so `transfer` returns `multisig_txset` and `submit_multisig` can broadcast after buyer and seller signing rounds.

## Security / trust model

- **Escrow:** Funds target a **2-of-3** policy (buyer, seller, coordinator). **Release** is intentionally **not** a single-party “send from custodial subaddress” in multisig mode: the API runs **prepare → independent buyer/seller signing steps → submit** so two peer keys participate before broadcast.
- **Payout addresses:** The buyer’s standard receive address (and optional bond return addresses) are agreed **out-of-band**; the MVP UI stores chat only in the browser—**use it to exchange Monero addresses**. The server never receives wallet seeds or remote-signing keys for buyer/seller.
- **Operational trust:** The coordinator still operates `wallet-rpc`, Tor, and the API; production deployments should harden auth, monitoring, and dispute policy separately.

## Authentication and accounts

- Register / login flow uses a **25-word Monero mnemonic** once at register; the server stores only a **user id** derived from the seed and issues **JWT** access tokens. Configure strong `ROBOSATS_XMR_JWT_SECRET` and `ROBOSATS_XMR_REGISTRATION_SECRET` in production.
- Trade `maker_id` / `taker_id` fields remain **client-supplied** in this MVP; binding every trade action to JWT is planned hardening.

## Environment variables (reference)

| Variable | Purpose |
|----------|---------|
| `ROBOSATS_XMR_DB_PATH` | SQLite path (default `data/trades.db`) |
| `ROBOSATS_XMR_USE_FAKE_WALLET` | `true` / `false` — developer/simulator vs `monero-wallet-rpc` |
| `MONERO_WALLET_RPC_URL` | Wallet JSON-RPC URL when not using the simulator |
| `MONERO_WALLET_RPC_USER` / `MONERO_WALLET_RPC_PASSWORD` | HTTP auth for wallet-rpc |
| `ROBOSATS_XMR_CORS_ORIGINS` | Comma-separated browser origins |
| `ROBOSATS_XMR_ESCROW_MODE` | **Unset = multisig (default).** Or `multisig` / `multisig_2of3` / `2of3`. Use `legacy` / `custodial` / `subaddress` / `single` for the old single-subaddress escrow. |
| `ROBOSATS_XMR_JWT_SECRET` | JWT HMAC secret |
| `ROBOSATS_XMR_REGISTRATION_SECRET` | Registration pepper |

## Tor (API)

With the `tor` service enabled in compose, read the onion hostname from the tor data volume (see compose comments) and reach the API over Tor Browser. The static Vite UI is not onion-hosted in-repo; host the built `frontend/dist` behind HTTPS or tunnel as needed.

## Key API endpoints

- `GET /status` — wallet mode, escrow mode, multisig readiness.
- `POST /auth/register/init`, `POST /auth/register/confirm`, `POST /auth/login`, `GET /auth/me`
- `POST /trades`, `GET /trades`, `GET /trades/{trade_id}`
- `POST /trades/{trade_id}/assign-deposit`, `refresh-funding`, `seed-confirmations` (dev-only confirmation injection for local testing)
- `POST /trades/{trade_id}/mark-fiat-paid`
- **Multisig release:** `POST /trades/{trade_id}/release-escrow/prepare`, `.../sign`, `.../submit`
- **Legacy release:** `POST /trades/{trade_id}/release-escrow` (only when `escrow_mode` is legacy)
- `POST /trades/{trade_id}/open-dispute`, `cancel`
- `POST /offers`, `GET /offers`, `POST /offers/{offer_id}/take`
- `GET /health`

## Background jobs

- Watcher: `python -m backend.watcher_main`
- Sweeper: `python -m backend.sweeper_main`

## Differences from original RoboSats

| Dimension | Original RoboSats | robosats-xmr |
|-----------|-------------------|--------------|
| Settlement | Lightning | Monero; **2-of-3 multisig escrow by default** with **prepare / peer sign / submit** and **10-block** funding finality; legacy single-subaddress opt-out |
| Accounts | RoboSats identity | 25-word Monero mnemonic → opaque `user_id` + JWT |
| Stack | LN nodes | `monerod` + `monero-wallet-rpc` + FastAPI |
| Frontend | Production RoboSats UI | MVP Vite app + local chat (address exchange) |

## Known limitations

- Trade chat is **not** end-to-end encrypted yet and is **browser-local** in the MVP.
- Trade actions are not fully **JWT-bound** to makers/takers in the API (identity fields are still client-supplied).
- Multisig **sign** steps identify `buyer` / `seller` by JSON field only; wallets should verify amounts/destinations before signing.

## Project docs

- `docs/SPEC.md`
- `docs/MILESTONES.md`
- `docs/TESTING.md`
