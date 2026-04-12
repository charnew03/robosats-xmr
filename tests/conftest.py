"""Pytest configuration: keep legacy single-subaddress escrow in tests unless overridden."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _escrow_mode_legacy_in_tests(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Production defaults to multisig; tests that assert `48xmr…` addresses opt into legacy here."""
    path = str(request.fspath)
    if path.endswith("test_multisig_escrow.py"):
        return
    monkeypatch.setenv("ROBOSATS_XMR_ESCROW_MODE", "legacy")
