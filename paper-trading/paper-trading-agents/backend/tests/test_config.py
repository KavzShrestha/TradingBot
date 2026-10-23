"""Tests for app.config settings loading."""

from decimal import Decimal

import pytest

from app.config import Settings


def test_settings_defaults_are_typed() -> None:
    settings = Settings()
    assert settings.paper_trading is True
    assert isinstance(settings.starting_capital, Decimal)
    assert settings.starting_capital == Decimal("100000")


def test_settings_from_env_reads_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPER_TRADING", "false")
    monkeypatch.setenv("STARTING_CAPITAL", "5000")
    settings = Settings.from_env()
    assert settings.paper_trading is False
    assert settings.starting_capital == Decimal("5000")
