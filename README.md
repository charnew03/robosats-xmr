# robosats-xmr

Monero-focused fork project inspired by RoboSats.

## Status

Phase 2 (settlement + disputes) in progress.

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

## Status & Next Steps

- Phase 1.5 funding slice is complete per the working agreement: funding tests and checklist items are green.
- Next work remains in later milestones (settlement/disputes hardening and broader operational controls), without changing the completed Phase 1.5 scope.

## Hardening (started early)

- Rate limiting middleware (basic in-memory)
- Seller open-trade limit (default max 3 open trades)
- Stale trade sweeper (module only; wiring into runner comes next)

## Working Agreement

No phase is marked complete unless required tests and checklists in `docs/TESTING.md` are green.
