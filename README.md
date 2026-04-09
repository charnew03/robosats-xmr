# robosats-xmr

A clean-slate FastAPI backend for a Monero-native RoboSats-style P2P fiat ↔ XMR exchange. Privacy-focused, no KYC, using 10-block escrow finality.

## Status & Next Steps

- ✅ Phase 1 (core trade creation, deposit assignment, funding/status handling) — COMPLETE
- ✅ Phase 2 (settlement + disputes) — COMPLETE
- ✅ Phase 3 (bonds + basic hardening) — COMPLETE
- Next milestone: extend hardening depth (bond reconciliation and abuse simulations) without changing completed phase behavior.

No phase is marked complete unless tests and checklists in `docs/TESTING.md` are green.

## Current Capabilities

| Area | What works today |
|---|---|
| Funding lifecycle | Create trade, assign escrow subaddress, refresh/watch confirmations, auto-mark `FUNDED` at threshold |
| Settlement lifecycle | `mark-fiat-paid`, `release-escrow`, `open-dispute` with guarded transitions |
| Bonds | Maker/taker bond amounts stored at trade creation, distinct bond subaddresses allocated, confirmation counters exposed |
| Bond returns | Optional maker/taker bond return sends on collaborative cancel and successful release |
| Risk controls | Seller max-open-trade limit enforced at creation |
| Maintenance jobs | Funding watcher and stale-trade sweeper loops with audit logging |

### Key API Endpoints

- `POST /trades`
- `GET /trades`
- `GET /trades/{trade_id}`
- `POST /trades/{trade_id}/assign-deposit`
- `POST /trades/{trade_id}/seed-confirmations` (fake-wallet test helper)
- `POST /trades/{trade_id}/refresh-funding`
- `POST /trades/{trade_id}/mark-fiat-paid`
- `POST /trades/{trade_id}/release-escrow` (`POST .../release` alias)
- `POST /trades/{trade_id}/open-dispute` (`POST .../dispute` alias)
- `POST /trades/{trade_id}/cancel`
- `GET /health`

## How to Run

### 1) Local dev (fake wallet, fastest)

1. Install Python 3.11+.
2. Install deps: `python -m pip install -r requirements-dev.txt`
3. Start API: `uvicorn backend.main:app --reload`
4. Open docs: `http://127.0.0.1:8000/docs`
5. Run tests: `pytest -q`

### 2) Real Monero mode (Docker stack)

1. Start stack: `docker compose up --build`
2. Services:
   - API: `http://127.0.0.1:8000`
   - `monerod` RPC: `http://127.0.0.1:18081`
   - `wallet-rpc` JSON-RPC: `http://127.0.0.1:18083`
3. Wallet init:
   - `wallet-init` service runs `docker/init-coordinator-wallet.sh` to create/open a coordinator wallet in wallet-rpc.
4. Enable API real wallet mode:
   - set `ROBOSATS_XMR_USE_FAKE_WALLET=false`
   - configure `MONERO_WALLET_RPC_URL`, `MONERO_WALLET_RPC_USER`, `MONERO_WALLET_RPC_PASSWORD`, `MONERO_WALLET_ACCOUNT_INDEX`

## Background Jobs

- Funding watcher: `python -m backend.watcher_main`
  - env: `ROBOSATS_XMR_WATCHER_INTERVAL_SECONDS` (default `10`)
- Stale trade sweeper: `python -m backend.sweeper_main`
  - env: `ROBOSATS_XMR_SWEEPER_INTERVAL_SECONDS` (default `300`)

## Differences from Original RoboSats

| Dimension | Original RoboSats (baseline) | robosats-xmr |
|---|---|---|
| Settlement rail | Lightning-native escrow flow | Monero subaddress-based custodial escrow |
| Finality signal | Lightning/payment flow semantics | 10-confirmation on-chain finality |
| Wallet backend | Lightning stack | `monerod` + `monero-wallet-rpc` |
| Hardening slice | Different guardrails/tooling | Bond fields, subaddress reconciliation, sweeper + risk-limit integration |

## Project Docs

- `docs/SPEC.md`
- `docs/MILESTONES.md`
- `docs/TESTING.md`
