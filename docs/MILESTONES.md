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

Status: in progress.

Deliverables:

- `FIAT_MARKED_PAID` and `RELEASED` flows.
- Dispute creation and moderator decision endpoints.
- Audit logging for every moderator action.

Testing gates:

- Integration tests for happy path release.
- Integration tests for dispute freeze and resolution.
- Regression checks for unauthorized release/refund actions.

## Phase 3 - Hardening and Abuse Controls

Status: started early (partial).

Deliverables:

- Rate limits and anti-spam controls.
- Trade/user risk limits (caps, cooldowns, open trade limits).
- Timeout sweeper and reconciliation jobs.

Testing gates:

- Adversarial tests (double submit, race conditions, replay-like behavior).
- Load smoke tests for critical endpoints.
- Backup/restore drill validation.

## Phase 4 - Public Staging and Bounty Submission

Deliverables:

- Public staging environment and operator runbook.
- Recorded end-to-end demo and dispute demo.
- Bounty submission package with evidence links.

Testing gates:

- Pre-release checklist fully green.
- No unresolved P0/P1 issues.
- Reproducible setup from clean environment.
