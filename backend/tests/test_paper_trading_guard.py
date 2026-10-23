"""Tests for CLAUDE.md Hard Rule #1: the PAPER_TRADING guard and the
live-endpoint denylist.

The app must refuse to start unless PAPER_TRADING=true, and must refuse any
base URL on the live-endpoint denylist in app/config.py.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Ensure get_settings()'s lru_cache never leaks state between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# -- Settings.validate_paper_trading_safe() -----------------------------------


def test_validate_raises_when_paper_trading_disabled() -> None:
    settings = Settings(paper_trading=False)
    with pytest.raises(RuntimeError, match="PAPER_TRADING"):
        settings.validate_paper_trading_safe()


@pytest.mark.parametrize(
    "live_url",
    [
        "https://api.alpaca.markets",
        "https://api.alpaca.markets/v2/orders",
        "https://api.binance.com",
        "https://api.exchange.coinbase.com",
        "https://api.kraken.com",
    ],
)
def test_validate_raises_when_base_url_is_denylisted(live_url: str) -> None:
    settings = Settings(paper_trading=True, data_base_url=live_url)
    with pytest.raises(RuntimeError, match="denylist"):
        settings.validate_paper_trading_safe()


def test_validate_passes_for_safe_paper_config() -> None:
    settings = Settings(
        paper_trading=True, data_base_url="https://paper-api.alpaca.markets"
    )
    settings.validate_paper_trading_safe()  # must not raise


def test_default_settings_are_safe() -> None:
    """The scaffold's defaults must themselves be paper-safe."""
    Settings().validate_paper_trading_safe()


# -- get_settings() enforces the guard ----------------------------------------


def test_get_settings_raises_when_paper_trading_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAPER_TRADING", "false")
    with pytest.raises(RuntimeError, match="PAPER_TRADING"):
        get_settings()


def test_get_settings_raises_when_base_url_denylisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("DATA_BASE_URL", "https://api.alpaca.markets")
    with pytest.raises(RuntimeError, match="denylist"):
        get_settings()


def test_get_settings_succeeds_with_safe_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("DATA_BASE_URL", "https://paper-api.alpaca.markets")
    settings = get_settings()
    assert settings.paper_trading is True


# -- create_app() genuinely refuses to start ----------------------------------


def test_create_app_refuses_to_start_when_not_paper_trading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAPER_TRADING", "false")
    with pytest.raises(RuntimeError, match="PAPER_TRADING"):
        create_app()


def test_create_app_refuses_to_start_with_live_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("DATA_BASE_URL", "https://api.binance.com")
    with pytest.raises(RuntimeError, match="denylist"):
        create_app()


def test_create_app_starts_with_safe_paper_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("DATA_BASE_URL", "https://paper-api.alpaca.markets")
    app = create_app()
    assert app.state.settings.paper_trading is True
