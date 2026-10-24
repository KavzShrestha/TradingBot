"""Tests for app.config settings loading."""

from decimal import Decimal

import pytest

from app.config import Settings


def test_settings_defaults_are_typed() -> None:
    settings = Settings()
    assert settings.paper_trading is True
    assert isinstance(settings.starting_capital, Decimal)
    assert settings.starting_capital == Decimal("100000")
    assert settings.data_base_url == "https://paper-api.alpaca.markets"


def test_settings_from_env_reads_data_base_url_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_BASE_URL", "https://sandbox.example.com")
    settings = Settings.from_env()
    assert settings.data_base_url == "https://sandbox.example.com"


def test_settings_from_env_reads_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPER_TRADING", "false")
    monkeypatch.setenv("STARTING_CAPITAL", "5000")
    settings = Settings.from_env()
    assert settings.paper_trading is False
    assert settings.starting_capital == Decimal("5000")


def test_market_data_url_on_denylist_is_refused() -> None:
    with pytest.raises(RuntimeError, match="MARKET_DATA_URL"):
        Settings(market_data_url="https://api.alpaca.markets").validate_paper_trading_safe()
