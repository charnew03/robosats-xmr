# SPEC v0.1

## Project Scope

Build a Monero-based trading platform fork with a RoboSats-like user flow, optimized for fast MVP delivery and safety-first operations.

## Product Goals

- Enable peer-to-peer trade coordination.
- Settle escrow in XMR for each trade.
- Minimize sensitive data collection and retention.
- Keep architecture upgradeable to stronger escrow models.

## Non-Goals (MVP)

- Native mobile clients.
- Advanced long-term reputation scoring.
- Automated fiat rail integrations.
- Support for assets beyond XMR.

## System Architecture (MVP)

- Web frontend: order creation, trade chat, status timeline, dispute actions.
- API backend: trade engine, state transitions, auth/session, moderation actions.
- Wallet service: `monero-wallet-rpc` integration for address generation, transfer detection, releases/refunds.
- Node service: self-hosted `monerod`.
- Database: users, orders, trades, ledger events, moderation events, dispute records.

## Trade State Machine

Primary flow:

1. `CREATED`
2. `FUNDS_PENDING`
3. `FUNDED` (10 confirmations)
4. `FIAT_MARKED_PAID`
5. `RELEASED`

Alternative exits:

- `CANCELLED` (before funded or by timeout policy)
- `DISPUTED` (manual moderator intervention)
- `REFUNDED` (cancellation/dispute outcome)

All transitions must be idempotent and event-logged.

## Escrow Model (MVP)

Custodial escrow with strict safety controls:

- Hard max trade notional.
- Daily volume cap per account.
- Max open trades per account.
- Cooling periods for newly created accounts.
- Manual release override only by authorized moderator role.

Future target:

- Replace custodial escrow with 2-of-3 multisig in a later milestone.

## Wallet and Confirmations

- One unique subaddress (or dedicated address strategy) per trade.
- Mark payment as "detected" at 1 confirmation for UX.
- Mark trade as funded/final at 10 confirmations.
- Auto-handle underpayment and overpayment events with clear operator runbook paths.

## Security and Privacy Baseline

- Tor support by default in docs and deployment examples.
- Avoid PII collection wherever possible.
- Store only operational metadata required to run disputes and audits.
- Encrypt sensitive secrets at rest.
- Enforce rate limits on auth, order creation, and chat actions.
- Audit-log all moderator actions.

## Dispute Handling (MVP)

- Dispute can be opened after `FUNDED`.
- Freeze release path until moderator action.
- Require structured dispute notes from both parties.
- Moderator decision must produce a signed audit event:
  - release to buyer, or
  - refund to seller.

## Operational Controls

- Wallet RPC health checks and alerts.
- Pending transfer reconciliation job.
- Stuck-trade timeout sweeper with safe defaults.
- Daily backup validation for database and wallet artifacts.

## Acceptance Criteria (Bounty-Oriented)

- Public code repository with setup instructions.
- Staging deployment available for test trades.
- End-to-end happy-path demo:
  - create order
  - open trade
  - fund trade in XMR
  - confirm fiat
  - release escrow
- Dispute demo:
  - open dispute
  - moderator decision
  - audited outcome
- Test suite covering core state transitions and error paths.

## Phase 3 (in progress) — Bonds and basic hardening

Custodial MVP extension (no non-custodial or advanced dispute resolution in this slice):

- Distinct subaddresses for **maker (seller) bond** and **taker (buyer) bond**, with configurable amounts at trade creation; addresses allocated at assign-deposit alongside trade escrow.
- **Risk limits**: e.g. max open trades per seller at creation time.
- **Stale trade sweeper**: cancel `CREATED` / `FUNDS_PENDING` trades past timeouts; audit-logged.
- **Collaborative cancel** before `FUNDED` via dedicated API action.

## Open Questions

- Preferred moderator governance model (single operator vs multi-moderator quorum).
- Regional/legal constraints for public operation.
- When to begin partial rollout of multisig design.
