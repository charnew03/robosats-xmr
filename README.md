# robosats-xmr

Monero-focused fork project inspired by RoboSats.

## Status

- ✅ Phase 1 (Core trade creation, deposit assignment, funding & status handling) — COMPLETE
- ✅ Phase 2 (settlement + disputes) — COMPLETE (see `docs/TESTING.md` checklist).
- Phase 3 (bonds + basic hardening) — IN PROGRESS (first slice: bonds, sweeper runner, collaborative cancel; see `docs/TESTING.md`).

## Objective

Build and deploy an MVP peer-to-peer trading platform using Monero settlement flows, with explicit tradeoffs documented and a clear path to stronger escrow models in later phases.

## MVP Decisions (Locked)

- Escrow model: custodial MVP with strict safety limits.
- Wallet backend: self-hosted `monerod` + `monero-wallet-rpc`.
- Funding threshold: 10 confirmations to mark trade funded/final.
- Network policy: Tor preferred + clearnet allowed.
- Out of scope: mobile app, advanced reputation, fiat API automation, multi-asset support.

## Docs

- `docs/SPEC.md`: architecture, state machine, risk controls, acceptance criteria.
- `docs/MILESTONES.md`: phased roadmap with deliverables.
- `docs/TESTING.md`: testing strategy and quality gates.

## Local Test Quickstart

1. Install Python 3.11+.
2. Run `python -m pip install -r requirements-dev.txt`.
3. Run `pytest -q`.

CI also runs tests on every push and pull request via GitHub Actions.

## API Slice (Phase 1.5)

Current endpoints:

- `POST /trades`
- `GET /trades/{trade_id}`
- `POST /trades/{trade_id}/assign-deposit`
- `POST /trades/{trade_id}/seed-confirmations` (testing helper endpoint)
- `POST /trades/{trade_id}/refresh-funding`
- `POST /trades/{trade_id}/mark-fiat-paid` (Phase 2)
- `POST /trades/{trade_id}/release-escrow` (Phase 2; `POST .../release` alias)
- `POST /trades/{trade_id}/open-dispute` (Phase 2; `POST .../dispute` alias)
- `POST /trades/{trade_id}/cancel` (Phase 3 — collaborative cancel before `FUNDED`)
- `GET /trades`
- `GET /health`

The API now persists trades to SQLite (`data/trades.db` by default).
Override with `ROBOSATS_XMR_DB_PATH` for tests or alternate environments.

Wallet mode:

- default dev mode: fake wallet RPC (`ROBOSATS_XMR_USE_FAKE_WALLET=true`)
- real wallet mode: set `ROBOSATS_XMR_USE_FAKE_WALLET=false` and configure:
  - `MONERO_WALLET_RPC_URL`
  - `MONERO_WALLET_RPC_USER`
  - `MONERO_WALLET_RPC_PASSWORD`
  - `MONERO_WALLET_ACCOUNT_INDEX` (optional, defaults to `0`)

## Current Capabilities

- Trades can be created and assigned a unique deposit address.
- Funding confirmation checks are available via API (`refresh-funding`) and via the background watcher loop.
- When confirmations reach the required threshold (10 by default), trades are automatically marked `FUNDED`.
- Once funded, trades are skipped by subsequent watcher polls.
- Trades can be read individually (`GET /trades/{trade_id}`) or listed (`GET /trades`) with consistent status and confirmation fields.

Phase 1 now supports:

- Core trade creation and persistence in SQLite.
- Deposit address assignment and pending-funding tracking.
- Manual and watcher-based funding detection with automatic `FUNDED` transition.
- Basic trade read/list endpoints for lifecycle visibility.

Phase 2 (settlement + disputes):

- `POST /trades/{trade_id}/mark-fiat-paid` — `FUNDED` → `FIAT_MARKED_PAID`.
- `POST /trades/{trade_id}/release-escrow` — `FIAT_MARKED_PAID` → `RELEASED`; sends the trade `amount_xmr` via `wallet_adapter.release_escrow_to_buyer` (full fake-wallet simulation; real `monero-wallet-rpc` transfer with subaddress scoping when derivable).
- `POST /trades/{trade_id}/open-dispute` — from `FUNDED` or `FIAT_MARKED_PAID` → `DISPUTED`; settlement actions are blocked; `RELEASED` / `DISPUTED` are terminal for this phase.

Phase 3 (first slice):

- **Maker/taker bonds** — amounts set on `POST /trades` (`maker_bond_amount_xmr`, `taker_bond_amount_xmr`, defaults `0.01`); separate subaddresses generated at `assign-deposit` (seller = maker, buyer = taker when present).
- **Risk limits** — max open trades per seller enforced at trade creation (`ROBOSATS_XMR_MAX_OPEN_TRADES_PER_SELLER`, default `3`).
- **Stale trade sweeper** — cancels timed-out `CREATED` / `FUNDS_PENDING` trades with audit logging; run periodically via `python -m backend.sweeper_main` (`ROBOSATS_XMR_SWEEPER_INTERVAL_SECONDS`, default `300`).
- **Collaborative cancel** — `POST .../cancel` while `CREATED` or `FUNDS_PENDING` only.

Some hardening (rate limits, open-trade cap, sweeper module) existed early; Phase 3 wires the **sweeper runner** and adds **bonds + cancel + audit** as above.

## Run API Locally

- Install runtime deps: `python -m pip install -r requirements.txt`
- Start API: `uvicorn backend.main:app --reload`
- Open docs: `http://127.0.0.1:8000/docs`

## Run with Docker

- Build and run: `docker compose up --build`
- API available at: `http://127.0.0.1:8000`

## Background Funding Watcher

- Run watcher loop: `python -m backend.watcher_main`
- Configure interval with `ROBOSATS_XMR_WATCHER_INTERVAL_SECONDS` (default `10`)
- Uses the same wallet mode environment variables as the API.
- The watcher automatically marks `FUNDS_PENDING` trades as `FUNDED` once confirmations reach the trade threshold (10 by default).
- Funded trades are skipped on later polls, so only pending deposits continue to be refreshed.

## Background Stale Trade Sweeper

- Run sweeper loop: `python -m backend.sweeper_main`
- Configure interval with `ROBOSATS_XMR_SWEEPER_INTERVAL_SECONDS` (default `300`)
- Uses `ROBOSATS_XMR_DB_PATH` (same DB as the API).
- Cancels stale `CREATED` and `FUNDS_PENDING` trades per `backend.sweeper` timeouts; writes `sweeper_cancel` audit rows when using SQLite.

## Status & Next Steps

- ✅ Phase 1 — COMPLETE | ✅ Phase 2 — COMPLETE | Phase 3 (bonds + basic hardening) — IN PROGRESS
- Phases 1 and 2 checklists in `docs/TESTING.md` are green; Phase 3 checklist tracks the current hardening slice (also in `docs/TESTING.md`).
- Next: extend Phase 3 (bond verification, reconciliation, deeper abuse tests) without regressing Phases 1–2.

No phase is marked complete unless tests and checklists in `docs/TESTING.md` are green (see **Working Agreement** below).

## Hardening (started early, Phase 3 integration)

- Rate limiting middleware (basic in-memory)
- Seller open-trade limit (default max 3 open trades)
- Stale trade sweeper module + **`sweeper_main` background runner** (Phase 3)

## Working Agreement

No phase is marked complete unless required tests and checklists in `docs/TESTING.md` are green.
