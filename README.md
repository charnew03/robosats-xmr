# robosats-xmr

A clean-slate FastAPI backend for a Monero-native RoboSats-style P2P fiat ↔ XMR exchange. Privacy-focused, no KYC, using 10-block escrow finality.

## Status & Next Steps

- Phase 1 (core trade creation, deposit assignment, funding/status handling) (completed)
- Phase 2 (settlement + disputes) (completed)
- Phase 3 (bonds + basic hardening) (completed)
- Phase 4 (Basic Order Book) (completed)
- **MVP frontend** — order book, create offer, dashboard, trade detail + local chat placeholder (see below) (completed)

No phase is marked complete unless tests and checklists in `docs/TESTING.md` are green.

## MVP Features

**Backend**

- Trade lifecycle: create, assign deposit, funding refresh + watcher (`FUNDED` at 10 confirmations), settlement (`mark-fiat-paid`, `release-escrow`), disputes, collaborative cancel
- Maker/taker bonds with subaddresses and confirmation counters
- Risk limits (max open trades per seller) and stale-trade sweeper
- **Order book:** `POST /offers`, `GET /offers`, `POST /offers/{id}/take` → bonded trade in `FUNDS_PENDING`
- Optional **Tor onion service** via Docker (`tor` service + hidden service to API)
- SQLite persistence, fake-wallet dev mode, real `monero-wallet-rpc` path

**Frontend** (`frontend/` — Vite + React + TypeScript + Tailwind)

- **Order book** (`/`): live `GET /offers`, filters (side, payment, min/max XMR, min/max premium), refresh, take-offer flow with modal
- **Create offer** (`/create-offer`): maker form → `POST /offers` (sell-XMR listings; buy-side reserved until API extends)
- **Dashboard** (`/dashboard`): “My active offers” + “Active trades” filtered by navbar **pseudonym**; links to trade detail
- **Trade detail** (`/trade/:id`): status, amounts, bonds, counterparty avatars; actions (refresh funding, mark fiat paid, release XMR, dispute, collaborative cancel); **trade chat** stored in **browser localStorage only** (MVP placeholder; E2E chat later)
- **Navigation:** top bar with pseudonym + colored avatar initials, routes via React Router
- Dark theme, toasts, loading states, mobile-friendly layouts

## How to Run

### 1) Local dev — API (fake wallet)

1. Python 3.11+
2. `python -m pip install -r requirements-dev.txt`
3. `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`
4. API docs: `http://127.0.0.1:8000/docs`
5. Tests: `pytest -q`

### 2) Local dev — frontend

1. Node.js LTS + npm (on Windows, if PowerShell blocks `npm`, use **cmd** or `npm.cmd`, or `Set-ExecutionPolicy RemoteSigned` for CurrentUser)
2. `cd frontend`
3. `npm install`
4. Copy `frontend/.env.example` to `frontend/.env` if needed (`VITE_API_BASE_URL=http://127.0.0.1:8000`)
5. `npm run dev -- --host 127.0.0.1`
6. Open the printed URL (e.g. `http://127.0.0.1:5173`)

Optional demo offers (API must be running):

```bash
python scripts/seed_demo_offers.py
```

### 3) Real Monero mode (Docker stack)

1. `docker compose up --build`
2. API: `http://127.0.0.1:8000` · `monerod` RPC: `18081` · wallet-rpc: `18083`
3. For **real** wallet RPC against the bundled `monerod` / `wallet-rpc`, use the merge file:  
   `docker compose -f docker-compose.yml -f docker-compose.stagenet-wallet.yml up --build`  
   (sets `ROBOSATS_XMR_USE_FAKE_WALLET=false` on the `api` service; RPC URL/user/password already match the compose stack)

### 4) Tor / onion service (API only)

1. `docker compose up --build -d` (includes `tor` service)
2. Onion hostname: `docker compose exec tor sh -lc "cat /var/lib/tor/robosats_api/hostname"`
3. In Tor Browser: `http://<hostname>.onion` (maps to API port 80 → container `api:8000`)
4. SOCKS5 for tooling: `127.0.0.1:9050`

The Vite frontend is not exposed as an onion service in this repo; use Tor Browser with a tunneled or separately hosted static build for full onion UI if needed.

## Stagenet testing (Docker + optional screen recording)

`docker-compose.yml` runs **monerod** and **monero-wallet-rpc** on **stagenet** (ports `18081` / `18083`). By default the **API** still uses the **fake wallet** so you can exercise the UI without coins. For **on-chain** stagenet behaviour, follow the steps below.

### Prerequisites

- Docker + Docker Compose
- Python 3.11+ on the host if you run the watcher outside Docker (same as [How to Run](#how-to-run) §1)
- Stagenet XMR for real funding (no monetary value): e.g. [Rino community stagenet faucet](https://community.rino.io/faucet/stagenet) or search for an active faucet; see [Monero networks (stagenet)](https://docs.getmonero.org/infrastructure/networks/). You will send to the **escrow/bond subaddresses** returned by the API/UI (from the coordinator wallet); understand that this is a custodial coordinator model for testing.

### 1) Start the stack (real wallet / on-chain mode)

From the repo root:

```bash
docker compose -f docker-compose.yml -f docker-compose.stagenet-wallet.yml up --build
```

Wait until `wallet-init` logs **Coordinator wallet ready.** and the API is listening on `http://127.0.0.1:8000`.

Optional checks:

- API docs: `http://127.0.0.1:8000/docs`
- Stagenet daemon RPC (host): `http://127.0.0.1:18081`
- Wallet RPC (host): `http://127.0.0.1:18083`

### 2) Funding watcher (recommended for demos)

The API does not mine blocks; confirmations move when **monerod** syncs and the watcher polls wallet RPC. In a **second terminal**, from the repo root (after `pip install -r requirements-dev.txt` or `requirements.txt`):

**Windows PowerShell:**

```powershell
$env:ROBOSATS_XMR_USE_FAKE_WALLET="false"
$env:MONERO_WALLET_RPC_URL="http://127.0.0.1:18083"
$env:ROBOSATS_XMR_DB_PATH="data/trades.db"
python -m backend.watcher_main
```

**cmd.exe:**

```bat
set ROBOSATS_XMR_USE_FAKE_WALLET=false
set MONERO_WALLET_RPC_URL=http://127.0.0.1:18083
set ROBOSATS_XMR_DB_PATH=data/trades.db
python -m backend.watcher_main
```

**bash:**

```bash
export ROBOSATS_XMR_USE_FAKE_WALLET=false
export MONERO_WALLET_RPC_URL=http://127.0.0.1:18083
export ROBOSATS_XMR_DB_PATH=data/trades.db
python -m backend.watcher_main
```

Use the same `ROBOSATS_XMR_DB_PATH` the API container uses (`./data` on the host maps to `/app/data` in the container).

### 3) Optional: stale-trade sweeper

Same `ROBOSATS_XMR_DB_PATH` as above; no wallet env vars needed.

```powershell
$env:ROBOSATS_XMR_DB_PATH="data/trades.db"
python -m backend.sweeper_main
```

### 4) Frontend + demo “clips” flow

1. Start the UI: `cd frontend`, `npm install`, `npm run dev -- --host 127.0.0.1` (see §2 under [How to Run](#how-to-run)).
2. Set `VITE_API_BASE_URL=http://127.0.0.1:8000` in `frontend/.env` if needed.
3. Record short clips in a logical order, for example:
   - **Stack health:** browser on `/docs` or `GET /health`, plus Docker Desktop showing services running.
   - **Order book:** list offers, filters, refresh.
   - **Create offer / take offer:** through to trade detail with escrow + bond addresses.
   - **On-chain funding:** send stagenet XMR to the shown subaddresses; show watcher logs as confirmations increase until `FUNDED` (default **10** confirmations).
   - **Settlement:** mark fiat paid → release escrow (and any bond behaviour you want to highlight).

### 5) Fake-wallet stagenet stack (UI only, no coins)

To run the same containers but keep **simulated** funding (good for quick UI captures without a faucet):

```bash
docker compose up --build
```

### Public demos

Place the API behind HTTPS or the optional **Tor** service; set `ROBOSATS_XMR_CORS_ORIGINS` so it includes your frontend origin.

## Bounty Status

**Ready for review** — Monero-native RoboSats-style fork with custodial subaddress escrow, 10-block finality, bonds, order book, settlement/disputes, basic frontend MVP, Docker stagenet stack, and optional Tor hidden service for API access. Further hardening (encrypted chat, full non-custodial path, production ops) can follow as separate milestones.

## Current Capabilities (summary)

| Area | What works |
|---|---|
| Funding | Escrow + confirmations, watcher, `FUNDED` threshold |
| Settlement | Fiat marked paid, XMR release, disputes |
| Bonds | Subaddresses, amounts, returns on cancel/release |
| Order book | Public offers, take → trade |
| Frontend | Book, create offer, dashboard, trade detail + MVP chat |
| Privacy | Dark UI, pseudonyms, optional Tor for API |

### Key API Endpoints

- `POST /trades`, `GET /trades`, `GET /trades/{trade_id}`
- `POST /trades/{trade_id}/assign-deposit`, `refresh-funding`, `seed-confirmations` (fake wallet)
- `POST /trades/{trade_id}/mark-fiat-paid`, `release-escrow`, `open-dispute`, `cancel`
- `POST /offers`, `GET /offers`, `POST /offers/{offer_id}/take`
- `GET /health`

## Background Jobs

- Funding watcher: `python -m backend.watcher_main` — `ROBOSATS_XMR_WATCHER_INTERVAL_SECONDS` (default `10`)
- Stale trade sweeper: `python -m backend.sweeper_main` — `ROBOSATS_XMR_SWEEPER_INTERVAL_SECONDS` (default `300`)

## Differences from Original RoboSats

| Dimension | Original RoboSats | robosats-xmr |
|---|---|---|
| Settlement | Lightning | Monero subaddress escrow |
| Finality | Payment semantics | 10 on-chain confirmations |
| Stack | LN nodes | `monerod` + `monero-wallet-rpc` |
| Frontend | Full prod UI | MVP Vite app + local chat placeholder |

## Project Docs

- `docs/SPEC.md`
- `docs/MILESTONES.md`
- `docs/TESTING.md`
