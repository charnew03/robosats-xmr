# robosats-xmr

A clean-slate FastAPI backend for a Monero-native RoboSats-style P2P fiat ↔ XMR exchange. Privacy-focused, no KYC, using 10-block escrow finality.

## Status & Next Steps

- ✅ Phase 1 (core trade creation, deposit assignment, funding/status handling) — COMPLETE
- ✅ Phase 2 (settlement + disputes) — COMPLETE
- ✅ Phase 3 (bonds + basic hardening) — COMPLETE
- ✅ Phase 4 (Basic Order Book) — COMPLETE
- ✅ **MVP frontend** — order book, create offer, dashboard, trade detail + local chat placeholder (see below)

No phase is marked complete unless tests and checklists in `docs/TESTING.md` are green.

## ✅ MVP Features

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
3. Set `ROBOSATS_XMR_USE_FAKE_WALLET=false` and wallet RPC env vars on the `api` service as documented in compose file comments

### 4) Tor / onion service (API only)

1. `docker compose up --build -d` (includes `tor` service)
2. Onion hostname: `docker compose exec tor sh -lc "cat /var/lib/tor/robosats_api/hostname"`
3. In Tor Browser: `http://<hostname>.onion` (maps to API port 80 → container `api:8000`)
4. SOCKS5 for tooling: `127.0.0.1:9050`

The Vite frontend is not exposed as an onion service in this repo; use Tor Browser with a tunneled or separately hosted static build for full onion UI if needed.

## Stagenet Demo

1. Use the provided **Docker Compose** stack (`monerod` + `wallet-rpc` are configured for **stagenet** in `docker-compose.yml`).
2. Start the stack, wait for wallet-init, set API env to **real wallet** mode (`ROBOSATS_XMR_USE_FAKE_WALLET=false`).
3. Run the **API** and optionally the **funding watcher** (`python -m backend.watcher_main`) and **sweeper** (`python -m backend.sweeper_main`) for realistic behaviour.
4. Run the **frontend** against the API base URL (localhost or LAN). Use **pseudonyms** in the UI; fund escrow/bond addresses shown in trade detail / API responses with stagenet XMR.
5. For a public demo, place the API behind HTTPS or onion; ensure CORS (`ROBOSATS_XMR_CORS_ORIGINS`) includes your frontend origin.

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
