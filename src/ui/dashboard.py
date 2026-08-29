from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, GLib, Gtk

from src.api.brapi import BrapiClient
from src.config.config_manager import AppConfig, ConfigManager
from src.ui.app_icon import make_settings_button, make_title_widget
from src.models.stock import ChartPeriod
from src.services.stock_service import StockService
from src.ui.settings import SettingsWindow, open_settings
from src.ui.stock_card import StockCard
from src.ui.stock_refresh import StockRefreshCoordinator
from src.ui.window_hints import get_window_origin, move_window

logger = logging.getLogger(__name__)


class DashboardWindow(Adw.ApplicationWindow):
    """Janela principal com grid de cards de ações (modo normal)."""

    def __init__(
        self,
        application: Adw.Application,
        service: StockService,
        config: AppConfig,
        config_manager: ConfigManager,
        default_period: ChartPeriod = ChartPeriod.ONE_DAY,
        *,
        client: BrapiClient | None = None,
    ) -> None:
        super().__init__(application=application, title="Stock Desktop")
        self._config = config
        self._config_manager = config_manager
        self._client = client
        self._settings_window: SettingsWindow | None = None
        self._stocks = [symbol.upper() for symbol in config.stocks]
        self._columns = max(config.columns, 1)
        self._cards: dict[str, StockCard] = {}

        self._coordinator = StockRefreshCoordinator(
            service=service,
            config=config,
            config_manager=config_manager,
            stocks=self._stocks,
            cards=self._cards,
            default_period=default_period,
        )

        self.set_default_size(config.window_width, config.window_height)
        self.set_resizable(False)

        toolbar = Adw.HeaderBar()
        toolbar.set_title_widget(make_title_widget())

        refresh_button = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_button.set_tooltip_text("Atualizar cotações e gráficos")
        refresh_button.connect("clicked", lambda *_: self._coordinator.refresh(full=True))
        toolbar.pack_end(refresh_button)

        settings_button = make_settings_button()
        settings_button.connect("clicked", self._on_settings_clicked)
        toolbar.pack_end(settings_button)

        self._grid = Gtk.Grid(
            column_spacing=8,
            row_spacing=8,
            column_homogeneous=True,
            row_homogeneous=False,
            halign=Gtk.Align.FILL,
            hexpand=True,
            valign=Gtk.Align.START,
        )

        for index, symbol in enumerate(self._stocks):
            period = self._coordinator.period_for_symbol(symbol)
            card = StockCard(
                symbol,
                default_period=period,
                on_period_changed=self._coordinator.on_period_changed,
                allowed_periods=self._coordinator.allowed_periods,
                compact=True,
            )
            card.set_hexpand(True)
            card.set_halign(Gtk.Align.FILL)
            card.set_valign(Gtk.Align.START)
            card.set_vexpand(False)
            card.set_size_request(-1, config.card_height)
            self._cards[symbol] = card
            row = index // self._columns
            column = index % self._columns
            self._grid.attach(card, column, row, 1, 1)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(self._grid)
        scroll.set_margin_top(8)
        scroll.set_margin_bottom(8)
        scroll.set_margin_start(8)
        scroll.set_margin_end(8)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(toolbar)
        main_box.append(scroll)
        self.set_content(main_box)

        self.connect("close-request", self._on_close_request)
        self.connect("realize", self._on_realize)

    def _on_realize(self, *_args: object) -> None:
        if self._config.window_x is not None and self._config.window_y is not None:
            move_window(self, self._config.window_x, self._config.window_y)
        self._coordinator.start()

    def _save_window_state(self) -> None:
        origin = get_window_origin(self)
        x = origin[0] if origin else None
        y = origin[1] if origin else None
        self._config_manager.update_window_state(
            self._config,
            width=self._config.window_width,
            height=self._config.window_height,
            x=x,
            y=y,
        )

    def _on_settings_clicked(self, *_args: object) -> None:
        self._settings_window = open_settings(
            self,
            self._config,
            self._config_manager,
            client=self._client,
            coordinator=self._coordinator,
            existing=self._settings_window,
        )

    def _on_close_request(self, *_args: object) -> bool:
        self._save_window_state()
        self._coordinator.stop()
        return False
