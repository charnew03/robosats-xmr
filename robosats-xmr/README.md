# robosats-xmr

Monero-focused fork project inspired by RoboSats.

## Status

Phase 0 (kickoff and specification).

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

## Working Agreement

No phase is marked complete unless required tests and checklists in `docs/TESTING.md` are green.
