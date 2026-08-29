from __future__ import annotations

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from src.config.config_manager import AppConfig, ConfigManager
from src.models.stock import ChartPeriod, StockHistory, StockQuote, interval_for_plan, periods_for_plan
from src.services.stock_service import StockService
from src.ui.stock_card import StockCard


class StockRefreshCoordinator:
    """Orquestra fetch de cotações/histórico para um conjunto de cards."""

    def __init__(
        self,
        service: StockService,
        config: AppConfig,
        config_manager: ConfigManager,
        stocks: list[str],
        cards: dict[str, StockCard],
        default_period: ChartPeriod,
    ) -> None:
        self._service = service
        self._config = config
        self._config_manager = config_manager
        self._stocks = [symbol.upper() for symbol in stocks]
        self._cards = cards
        self._default_period = default_period
        self._allowed_periods = periods_for_plan(config.api_plan)
        if self._default_period not in self._allowed_periods:
            self._default_period = ChartPeriod.ONE_DAY
        self._refresh_interval_ms = max(config.refresh_interval, 60) * 1000
        self._refresh_source_id: int | None = None

    def period_for_symbol(self, symbol: str) -> ChartPeriod:
        saved = self._config.card_periods.get(symbol.upper())
        if saved:
            period = ChartPeriod.from_api_range(saved)
            if period and period in self._allowed_periods:
                return period
        if self._default_period in self._allowed_periods:
            return self._default_period
        return ChartPeriod.ONE_DAY

    @property
    def allowed_periods(self) -> frozenset[ChartPeriod]:
        return self._allowed_periods

    def start(self) -> None:
        self.refresh(full=True)
        self._refresh_source_id = GLib.timeout_add(
            self._refresh_interval_ms,
            self._on_refresh_timer,
        )

    def stop(self) -> None:
        if self._refresh_source_id is not None:
            GLib.source_remove(self._refresh_source_id)
            self._refresh_source_id = None
        self._service.shutdown()

    def set_refresh_interval(self, seconds: int) -> None:
        self._refresh_interval_ms = max(seconds, 60) * 1000
        if self._refresh_source_id is not None:
            GLib.source_remove(self._refresh_source_id)
        self._refresh_source_id = GLib.timeout_add(
            self._refresh_interval_ms,
            self._on_refresh_timer,
        )

    def _on_refresh_timer(self) -> bool:
        self.refresh(full=False)
        return True

    def refresh(self, *, full: bool = False) -> None:
        self._fetch_quotes()
        if full:
            for symbol, card in self._cards.items():
                self._fetch_history(symbol, card.period, force_refresh=True)

    def on_period_changed(self, symbol: str, period: ChartPeriod) -> None:
        self._config_manager.set_card_period(self._config, symbol, period.range)
        self._fetch_history(symbol, period)

    def _fetch_quotes(self) -> None:
        self._service.fetch_quotes_async(
            self._stocks,
            on_success=self._on_quotes_received,
        )

    def _fetch_history(
        self,
        symbol: str,
        period: ChartPeriod,
        *,
        force_refresh: bool = False,
    ) -> None:
        def on_success(history: StockHistory) -> bool | None:
            card = self._cards.get(symbol)
            if card:
                card.update_history(history)
            return False

        self._service.fetch_history_async(
            symbol,
            period,
            on_success=on_success,
            interval=interval_for_plan(period, self._config.api_plan),
            force_refresh=force_refresh,
        )

    def _on_quotes_received(self, quotes: list[StockQuote]) -> bool | None:
        for quote in quotes:
            card = self._cards.get(quote.symbol.upper())
            if card:
                card.update_quote(quote)
        return False
