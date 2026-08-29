from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from src.api.brapi import BrapiClient
from src.config.config_manager import AppConfig, ConfigManager
from src.models.stock import ChartPeriod
from src.services.stock_service import StockService
from src.ui.desktop_window import StockWidgetWindow
from src.ui.stock_card import StockCard
from src.ui.stock_refresh import StockRefreshCoordinator
from src.ui.widget_panel import WidgetPanelWindow
from src.ui.window_hints import is_wayland

logger = logging.getLogger(__name__)


def default_card_position(
    index: int,
    *,
    card_width: int,
    card_height: int,
    columns: int = 3,
    margin: int = 24,
    gap: int = 16,
) -> tuple[int, int]:
    column = index % columns
    row = index // columns
    x = margin + column * (card_width + gap)
    y = margin + row * (card_height + gap)
    return x, y


class WidgetDesktop:
    """Modo desktop: grid em uma janela (Wayland) ou uma janela por ação (X11)."""

    def __init__(
        self,
        application: Adw.Application,
        service: StockService,
        config: AppConfig,
        config_manager: ConfigManager,
        default_period: ChartPeriod,
        *,
        client: BrapiClient,
    ) -> None:
        self._application = application
        self._config = config
        self._config_manager = config_manager
        self._client = client
        self._cards: dict[str, StockCard] = {}
        self._windows: list[StockWidgetWindow] = []
        self._panel: WidgetPanelWindow | None = None
        self._use_panel = is_wayland()

        self._coordinator = StockRefreshCoordinator(
            service=service,
            config=config,
            config_manager=config_manager,
            stocks=config.stocks,
            cards=self._cards,
            default_period=default_period,
        )

        stocks = [symbol.upper() for symbol in config.stocks]
        for symbol in stocks:
            period = self._coordinator.period_for_symbol(symbol)
            card = StockCard(
                symbol,
                default_period=period,
                on_period_changed=self._coordinator.on_period_changed,
                allowed_periods=self._coordinator.allowed_periods,
                compact=True,
                use_window_handle=not self._use_panel,
            )
            if self._use_panel:
                card.set_hexpand(True)
                card.set_halign(Gtk.Align.FILL)
                card.set_valign(Gtk.Align.FILL)
                card.set_vexpand(True)
            else:
                card.set_size_request(config.card_width, config.card_height)
            self._cards[symbol] = card

        if self._use_panel:
            logger.info(
                "Wayland detectado: widgets em uma janela frameless com grid "
                "(posicionamento livre por janela não suportado pelo compositor)"
            )
            self._panel = WidgetPanelWindow(
                application,
                config,
                config_manager,
                stocks,
                self._cards,
                config.columns,
                on_close=self._on_panel_closed,
                client=self._client,
                coordinator=self._coordinator,
            )
        else:
            for index, symbol in enumerate(stocks):
                x, y = self._position_for_symbol(symbol, index)
                window = StockWidgetWindow(
                    application,
                    symbol,
                    self._cards[symbol],
                    config,
                    config_manager,
                    x=x,
                    y=y,
                    on_close=self._on_window_closed,
                )
                self._windows.append(window)

        self._coordinator.start()

    def _position_for_symbol(self, symbol: str, index: int) -> tuple[int, int]:
        saved = self._config.card_positions.get(symbol)
        if saved and "x" in saved and "y" in saved:
            return int(saved["x"]), int(saved["y"])
        return default_card_position(
            index,
            card_width=self._config.card_width,
            card_height=self._config.card_height,
            columns=self._config.columns,
        )

    def present_all(self) -> None:
        if self._panel is not None:
            self._panel.present()
            return
        for window in self._windows:
            window.present()

    def _shutdown(self) -> None:
        logger.info("Encerrando modo widget")
        self._coordinator.stop()
        self._application.quit()

    def _on_panel_closed(self, _panel: WidgetPanelWindow) -> None:
        self._shutdown()

    def _on_window_closed(self, window: StockWidgetWindow) -> None:
        if window in self._windows:
            self._windows.remove(window)
        if not self._windows:
            self._shutdown()
