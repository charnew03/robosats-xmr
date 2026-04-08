# Milestones v0.1

## Phase 0 - Kickoff and Alignment (completed)

Deliverables:

- Bounty claim posted publicly.
- MVP architecture decisions locked.
- Initial docs published (`README`, `SPEC`, `MILESTONES`, `TESTING`).
- Acceptance criteria draft prepared for maintainer feedback.

Exit criteria:

- All Phase 0 checklist items complete.

## Phase 1 - Vertical Slice (Monero funding path) (completed)

Deliverables:

- Project scaffold and local dev environment.
- Wallet RPC connectivity and health checks.
- Trade creation + unique address assignment.
- Confirmation watcher with transition to `FUNDED`.

Testing gates:

- Unit tests for wallet adapter and transition guards.
- Integration test for trade funding detection.
- Manual smoke test with testnet/stagenet funds.

## Phase 2 - Settlement and Disputes

Status: completed (buyer/seller settlement paths, dispute freeze; see `docs/TESTING.md`).

Deliverables:

- `FIAT_MARKED_PAID` and `RELEASED` flows.
- Dispute creation with settlement freeze while `DISPUTED`.
- Audit logging for settlement actions.

Testing gates:

- Integration tests for happy path release.
- Integration tests for dispute freeze and invalid transitions.

## Phase 3 - Bonds, hardening, and abuse controls

Status: in progress (first slice: bonds + sweeper wiring + collaborative cancel).

Deliverables:

- Maker/taker bond subaddresses and amounts (custodial); integrated at assign-deposit.
- Rate limits and anti-spam controls (partial, existing middleware).
- Trade/user risk limits (open trades per seller at creation).
- Stale-trade timeout sweeper with background runner and audit events.
- Collaborative cancel before `FUNDED`.

Testing gates:

- Tests for bond assignment, risk limits, sweeper behavior, and cancel (fake wallet).
- Adversarial tests (double submit, race conditions) in later Phase 3 iterations.
- Backup/restore drill validation (later).

## Phase 4 - Public Staging and Bounty Submission

Deliverables:

- Public staging environment and operator runbook.
- Recorded end-to-end demo and dispute demo.
- Bounty submission package with evidence links.

Testing gates:

- Pre-release checklist fully green.
- No unresolved P0/P1 issues.
- Reproducible setup from clean environment.
