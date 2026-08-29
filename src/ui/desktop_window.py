from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from src.config.config_manager import AppConfig, ConfigManager
from src.ui.app_icon import apply_window_icon
from src.ui.stock_card import StockCard
from src.ui.window_hints import apply_desktop_widget_hints, get_window_origin, move_window

logger = logging.getLogger(__name__)


class StockWidgetWindow(Gtk.Window):
    """Janela frameless com um card, arrastável pelo cabeçalho."""

    def __init__(
        self,
        application: Gtk.Application,
        symbol: str,
        card: StockCard,
        config: AppConfig,
        config_manager: ConfigManager,
        *,
        x: int,
        y: int,
        on_close: Callable[["StockWidgetWindow"], None],
    ) -> None:
        super().__init__(application=application)
        self._symbol = symbol.upper()
        self._card = card
        self._config = config
        self._config_manager = config_manager
        self._on_close_callback = on_close
        self._drag_origin_x = 0
        self._drag_origin_y = 0
        self._window_x = x
        self._window_y = y

        self.set_title(f"Stock Desktop — {self._symbol}")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(config.card_width, config.card_height)
        self.add_css_class("widget-window")

        self._card.add_css_class("compact")
        self._card.set_margin_top(0)
        self._card.set_margin_bottom(0)
        self._card.set_margin_start(0)
        self._card.set_margin_end(0)
        self.set_child(self._card)

        if not self._card.uses_native_drag:
            self._setup_drag()
        self.connect("realize", self._on_realize)
        self.connect("close-request", self._on_close_request)

    def _setup_drag(self) -> None:
        gesture = Gtk.GestureDrag()
        gesture.set_button(0)
        gesture.connect("drag-begin", self._on_drag_begin)
        gesture.connect("drag-update", self._on_drag_update)
        gesture.connect("drag-end", self._on_drag_end)
        self._card.drag_handle.add_controller(gesture)

    def _on_realize(self, *_args: object) -> None:
        apply_window_icon(self)
        apply_desktop_widget_hints(self)
        if not move_window(self, self._window_x, self._window_y):
            logger.debug(
                "Posição inicial de %s pode não ter sido aplicada (Wayland)",
                self._symbol,
            )

    def _on_drag_begin(
        self,
        _gesture: Gtk.GestureDrag,
        _start_x: float,
        _start_y: float,
    ) -> None:
        origin = get_window_origin(self)
        if origin is not None:
            self._drag_origin_x, self._drag_origin_y = origin
        else:
            self._drag_origin_x, self._drag_origin_y = self._window_x, self._window_y

    def _on_drag_update(
        self,
        _gesture: Gtk.GestureDrag,
        offset_x: float,
        offset_y: float,
    ) -> None:
        new_x = self._drag_origin_x + int(offset_x)
        new_y = self._drag_origin_y + int(offset_y)
        if move_window(self, new_x, new_y):
            self._window_x, self._window_y = new_x, new_y

    def _on_drag_end(
        self,
        _gesture: Gtk.GestureDrag,
        _offset_x: float,
        _offset_y: float,
    ) -> None:
        self._save_position()

    def _save_position(self) -> None:
        origin = get_window_origin(self)
        if origin is not None:
            self._window_x, self._window_y = origin
        self._config_manager.set_card_position(
            self._config,
            self._symbol,
            self._window_x,
            self._window_y,
        )

    def _on_close_request(self, *_args: object) -> bool:
        self._save_position()
        self._on_close_callback(self)
        return False
