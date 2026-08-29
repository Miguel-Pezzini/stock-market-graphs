from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from src.api.brapi import BrapiClient
from src.config.config_manager import AppConfig, ConfigManager
from src.ui.app_icon import apply_window_icon, make_app_icon_image, make_settings_button
from src.ui.settings import SettingsWindow, open_settings
from src.ui.stock_card import StockCard
from src.ui.stock_refresh import StockRefreshCoordinator
from src.ui.window_hints import apply_desktop_widget_hints, get_window_origin, move_window

logger = logging.getLogger(__name__)


class WidgetPanelWindow(Gtk.Window):
    """Uma janela frameless com grid de cards (necessário no Wayland/GNOME)."""

    GRID_GAP = 8
    TITLE_BAR_HEIGHT = 30
    MAX_PANEL_HEIGHT = 360

    def __init__(
        self,
        application: Gtk.Application,
        config: AppConfig,
        config_manager: ConfigManager,
        stocks: list[str],
        cards: dict[str, StockCard],
        columns: int,
        on_close: Callable[["WidgetPanelWindow"], None],
        *,
        client: BrapiClient | None = None,
        coordinator: StockRefreshCoordinator | None = None,
    ) -> None:
        super().__init__(application=application)
        self._config = config
        self._config_manager = config_manager
        self._on_close_callback = on_close
        self._client = client
        self._coordinator = coordinator
        self._settings_window: SettingsWindow | None = None
        self._window_x = config.window_x or 80
        self._window_y = config.window_y or 80

        self.set_title("Stock Desktop")
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("widget-window")

        columns = max(columns, 1)
        stock_count = len(stocks)
        card_width = config.card_width
        card_height = config.card_height

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.add_css_class("widget-panel")
        panel.set_vexpand(False)

        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        title_bar.add_css_class("widget-drag-bar")
        title_bar.set_halign(Gtk.Align.FILL)
        title_bar.set_vexpand(False)

        drag_handle = Gtk.WindowHandle()
        drag_handle.set_hexpand(True)
        drag_handle.set_halign(Gtk.Align.FILL)
        drag_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        drag_title.set_margin_start(8)
        drag_title.append(make_app_icon_image(pixel_size=16))
        drag_label = Gtk.Label(label="Arraste para mover")
        drag_label.add_css_class("widget-drag-label")
        drag_label.set_halign(Gtk.Align.START)
        drag_label.set_xalign(0)
        drag_title.append(drag_label)
        drag_handle.set_child(drag_title)
        title_bar.append(drag_handle)

        settings_button = make_settings_button()
        settings_button.add_css_class("flat")
        settings_button.add_css_class("widget-close-button")
        settings_button.set_valign(Gtk.Align.CENTER)
        settings_button.set_vexpand(False)
        settings_button.set_margin_top(4)
        settings_button.set_margin_bottom(4)
        settings_button.connect("clicked", self._on_settings_clicked)
        title_bar.append(settings_button)

        close_button = Gtk.Button()
        close_button.set_icon_name("window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.add_css_class("widget-close-button")
        close_button.set_tooltip_text("Fechar")
        close_button.set_valign(Gtk.Align.CENTER)
        close_button.set_vexpand(False)
        close_button.set_margin_top(4)
        close_button.set_margin_bottom(4)
        close_button.set_margin_end(6)
        close_button.connect("clicked", lambda *_: self.close())
        title_bar.append(close_button)

        panel.append(title_bar)

        grid = Gtk.Grid(
            column_spacing=self.GRID_GAP,
            row_spacing=self.GRID_GAP,
            column_homogeneous=True,
            row_homogeneous=False,
            margin_top=self.GRID_GAP,
            margin_bottom=self.GRID_GAP,
            margin_start=self.GRID_GAP,
            margin_end=self.GRID_GAP,
            hexpand=False,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.START,
            vexpand=False,
        )

        for index, symbol in enumerate(stocks):
            card = cards[symbol.upper()]
            card.set_size_request(card_width, card_height)
            row = index // columns
            column = index % columns
            grid.attach(card, column, row, 1, 1)

        content_height = self._content_height(stock_count, columns, card_height)
        content_width = self._content_width(stock_count, columns, card_width)

        if content_height > self.MAX_PANEL_HEIGHT:
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.set_vexpand(False)
            scroll.set_size_request(content_width, self.MAX_PANEL_HEIGHT)
            scroll.set_child(grid)
            panel.append(scroll)
            self._panel_width = content_width
            self._panel_height = self.TITLE_BAR_HEIGHT + self.MAX_PANEL_HEIGHT
        else:
            panel.append(grid)
            self._panel_width = content_width
            self._panel_height = content_height

        self._apply_window_size()

        self.set_child(panel)
        self.connect("realize", self._on_realize)
        self.connect("close-request", self._on_close_request)

    @classmethod
    def _content_height(cls, stock_count: int, columns: int, card_height: int) -> int:
        rows = max(1, (stock_count + columns - 1) // columns)
        return (
            cls.TITLE_BAR_HEIGHT
            + cls.GRID_GAP * 2
            + rows * card_height
            + max(0, rows - 1) * cls.GRID_GAP
        )

    @classmethod
    def _content_width(cls, stock_count: int, columns: int, card_width: int) -> int:
        visible_columns = min(columns, max(stock_count, 1))
        return (
            visible_columns * card_width
            + (visible_columns + 1) * cls.GRID_GAP
        )

    def _apply_window_size(self) -> None:
        self.set_default_size(self._panel_width, self._panel_height)
        self.set_size_request(self._panel_width, self._panel_height)

    def _on_settings_clicked(self, *_args: object) -> None:
        self._settings_window = open_settings(
            self,
            self._config,
            self._config_manager,
            client=self._client,
            coordinator=self._coordinator,
            existing=self._settings_window,
        )

    def _on_realize(self, *_args: object) -> None:
        apply_window_icon(self)
        self._apply_window_size()
        apply_desktop_widget_hints(self)
        if not move_window(self, self._window_x, self._window_y):
            logger.debug(
                "Posição inicial do painel pode não ter sido aplicada (Wayland)"
            )

    def _save_state(self) -> None:
        origin = get_window_origin(self)
        x = origin[0] if origin else self._window_x
        y = origin[1] if origin else self._window_y
        if origin is not None:
            self._window_x, self._window_y = x, y
        self._config_manager.update_window_state(
            self._config,
            width=self._panel_width,
            height=self._panel_height,
            x=x,
            y=y,
        )

    def _on_close_request(self, *_args: object) -> bool:
        self._save_state()
        self._on_close_callback(self)
        return False
