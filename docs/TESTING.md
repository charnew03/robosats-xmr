# Testing Strategy v0.1

## Rule

No milestone is complete until tests for that milestone pass locally and evidence is recorded.

## Test Pyramid

- Unit tests: business rules, validators, transition guards.
- Integration tests: API + DB + wallet adapter interactions.
- End-to-end smoke tests: realistic user journey in staging.

## Required Test Coverage by Domain

- Trade state machine transitions and invalid transition rejection.
- Wallet event parsing and confirmation threshold logic.
- Release/refund decision paths including disputes.
- Permission boundaries for traders vs moderators.
- Timeout and reconciliation background jobs.

## Bug-Fix Workflow

1. Reproduce with a failing test first.
2. Fix code in smallest safe scope.
3. Re-run impacted tests and one-level-up regression tests.
4. Record root cause and prevention note.

## Per-PR Quality Gates

- New logic includes tests.
- Existing tests remain green.
- No unresolved critical lints or type errors.
- Changelog note for behavior-affecting changes.

## Regression Matrix (minimum)

- Normal funding and release.
- Underpayment.
- Late payment after timeout.
- Simultaneous actor actions (race-like conditions).
- Dispute opened before/after fiat marked paid.
- Moderator authorization failure paths.

## Release Readiness Checklist

- End-to-end happy path validated on staging.
- Dispute flow validated on staging.
- Wallet/node restart recovery test passed.
- Backup and restore tested from fresh environment.
- Open critical bug count is zero.

## Phase 1 Core Checklist

- [x] `POST /trades` creates a trade with initial state `CREATED`.
- [x] `POST /trades/{trade_id}/assign-deposit` stores a unique deposit address and transitions to `FUNDS_PENDING`.
- [x] Funding confirmation works via manual refresh (`POST /trades/{trade_id}/refresh-funding`) and watcher polling.
- [x] Trade transitions to `FUNDED` automatically at `>= required_confirmations` (default 10).
- [x] `GET /trades/{trade_id}` returns current state and confirmation fields consistently.
- [x] `GET /trades` returns persisted trades for basic read/list flow.
- [x] SQLite persistence is validated through API and repository tests.
- [x] Fake wallet mode and real wallet RPC mode are both supported by configuration.

## Phase 1.5 Funding Checklist

- [x] `POST /trades` creates trade in `CREATED`.
- [x] `POST /trades/{trade_id}/assign-deposit` sets `FUNDS_PENDING` and deposit address.
- [x] Confirmation source is updated (via `seed-confirmations` in fake-wallet tests, or wallet RPC on watcher runs).
- [x] Watcher poll (`run_funding_refresh_once` / loop) auto-transitions trade to `FUNDED` at `>= required_confirmations` (default 10).
- [x] Once `FUNDED`, subsequent watcher polls skip the trade.
- [x] `POST /trades/{trade_id}/refresh-funding` returns consistent `state` and `current_confirmations`.
- [x] `pytest -q` is green before Phase 1.5 is marked complete.

## Phase 2 Settlement + Disputes Checklist

- [x] Trade model includes `FIAT_MARKED_PAID`, `RELEASED`, and `DISPUTED` (see `trade_engine.py` and `ALLOWED_TRANSITIONS`).
- [x] `FUNDED` → `FIAT_MARKED_PAID` only via `mark_fiat_paid`; `FIAT_MARKED_PAID` → `RELEASED` only via `set_release` after `release_escrow_to_buyer`; `FUNDED` or `FIAT_MARKED_PAID` → `DISPUTED` via `open_dispute`.
- [x] `RELEASED` and `DISPUTED` are terminal for Phase 2 settlement (no transitions out of `DISPUTED` in this phase).
- [x] `POST /trades/{trade_id}/mark-fiat-paid` validates state, persists, audit + logging.
- [x] `POST /trades/{trade_id}/release-escrow` validates `FIAT_MARKED_PAID`, calls `wallet_adapter.release_escrow_to_buyer` (fake simulation + real RPC with optional `subaddr_indices`), persists `release_txid`, audit + logging.
- [x] `POST /trades/{trade_id}/open-dispute` freezes settlement (`mark-fiat-paid`, `release-escrow` rejected); rejects duplicate dispute and post-`RELEASED` attempts.
- [x] Basic audit events: `fiat_marked_paid`, `release_escrow`, `dispute_opened`.
- [x] Integration tests: happy path (`FUNDED` → mark-fiat → release-escrow with fake txid); dispute from `FUNDED` and from `FIAT_MARKED_PAID`; invalid transition coverage; persistence of `release_txid` / disputed fields (see `tests/test_repository.py`).
- [x] `pytest -q` green for Phase 2 paths (per working agreement below).

## Phase 3 Bonds + Basic Hardening Checklist (In progress — first slice)

- [x] Maker/taker bond amounts on trade creation; bond subaddresses at `assign-deposit` (wallet / fake wallet).
- [x] Trade API responses include bond fields (`maker_bond_*`, `taker_bond_*`).
- [x] Seller open-trade limit enforced at `POST /trades` (`risk_limits`).
- [x] Stale trade sweeper cancels expired `CREATED` / `FUNDS_PENDING` and writes `sweeper_cancel` audit events (SQLite).
- [x] Background sweeper runner: `python -m backend.sweeper_main` (`ROBOSATS_XMR_SWEEPER_INTERVAL_SECONDS`).
- [x] Collaborative cancel: `POST /trades/{trade_id}/cancel` before `FUNDED`, with audit trail.
- [x] Audit event `bonds_assigned` on assign-deposit.
- [x] `pytest -q` green including Phase 3 tests.
- [ ] Further Phase 3: bond funding verification, reconciliation jobs, deeper abuse/adversarial tests.
