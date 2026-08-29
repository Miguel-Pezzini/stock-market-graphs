from __future__ import annotations

import logging
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gio, Gtk

from src.api.brapi import BrapiClient
from src.config.config_manager import ConfigManager
from src.models.stock import ChartPeriod
from src.services.stock_service import StockService
from src.ui.app_icon import setup_application_icon
from src.ui.dashboard import DashboardWindow
from src.ui.theme import apply_theme
from src.ui.widget_desktop import WidgetDesktop

APP_ID = "com.stockdesktop.app"

_CUSTOM_CSS = """
.stock-card {
  background-image: linear-gradient(
    165deg,
    alpha(#ffffff, 0.07) 0%,
    alpha(#ffffff, 0.03) 50%,
    alpha(#000000, 0.06) 100%
  );
  background-color: alpha(currentColor, 0.03);
  border: 1px solid alpha(#ffffff, 0.09);
  border-radius: 14px;
  padding: 14px;
  box-shadow:
    0 1px 0 alpha(#ffffff, 0.05) inset,
    0 6px 20px alpha(#000000, 0.14);
}
.stock-card.compact {
  padding: 14px 12px 10px 12px;
  border-radius: 12px;
  box-shadow:
    0 1px 0 alpha(#ffffff, 0.06) inset,
    0 4px 14px alpha(#000000, 0.16);
}
.stock-card.compact .card-header {
  min-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
.stock-card.compact .stock-ticker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  opacity: 0.72;
  padding-top: 0;
  padding-bottom: 0;
}
.stock-card.compact .stock-name {
  font-size: 10px;
  margin-top: -2px;
  margin-bottom: 2px;
}
.stock-card.compact .stock-price {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-top: 2px;
  margin-bottom: 6px;
}
.stock-card.compact .stock-change {
  font-size: 11px;
  font-weight: 700;
}
.stock-card.compact .change-badge {
  padding: 3px 8px;
  border-radius: 999px;
}
.stock-card.compact .change-badge.success {
  background-image: linear-gradient(
    180deg,
    alpha(#2ec27e, 0.22) 0%,
    alpha(#2ec27e, 0.12) 100%
  );
}
.stock-card.compact .change-badge.error {
  background-image: linear-gradient(
    180deg,
    alpha(#e01b24, 0.22) 0%,
    alpha(#e01b24, 0.12) 100%
  );
}
.stock-card.compact .chart-area {
  margin-top: 0;
  margin-bottom: 8px;
  min-height: 56px;
}
.stock-card.compact .period-bar {
  padding: 4px;
  border-radius: 8px;
  margin-top: 0;
  background-image: linear-gradient(
    180deg,
    alpha(#000000, 0.14) 0%,
    alpha(#000000, 0.06) 100%
  );
  background-color: alpha(currentColor, 0.04);
}
.stock-card.compact .period-toggle {
  min-height: 28px;
  min-width: 0;
  padding: 0;
  border-radius: 6px;
  opacity: 0.48;
}
.stock-card.compact .period-toggle label,
.stock-card.compact .period-toggle-label {
  font-size: 11px;
  font-weight: 700;
  padding: 7px 0;
}
.stock-card.compact .period-toggle:checked {
  opacity: 1;
  background-image: linear-gradient(
    180deg,
    shade(@accent_bg_color, 1.12),
    @accent_bg_color
  );
  box-shadow: 0 1px 3px alpha(@accent_bg_color, 0.3);
}
.stock-ticker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  opacity: 0.65;
}
.stock-name {
  font-size: 11px;
  font-weight: 400;
  opacity: 0.42;
  margin-top: -1px;
  margin-bottom: 2px;
}
.stock-price {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-top: 6px;
  margin-bottom: 4px;
}
.stock-change {
  font-size: 12px;
  font-weight: 700;
}
.change-badge {
  border-radius: 999px;
  padding: 3px 9px;
}
.change-badge.success {
  background-image: linear-gradient(
    180deg,
    alpha(#2ec27e, 0.2) 0%,
    alpha(#2ec27e, 0.1) 100%
  );
}
.change-badge.error {
  background-image: linear-gradient(
    180deg,
    alpha(#e01b24, 0.2) 0%,
    alpha(#e01b24, 0.1) 100%
  );
}
.change-badge.neutral {
  background-color: alpha(currentColor, 0.08);
}
label.success {
  color: #2ec27e;
}
label.error {
  color: #e01b24;
}
.chart-area {
  margin-top: 2px;
  margin-bottom: 10px;
  min-height: 72px;
}
.period-bar {
  background-image: linear-gradient(
    180deg,
    alpha(#000000, 0.1) 0%,
    alpha(#000000, 0.04) 100%
  );
  background-color: alpha(currentColor, 0.05);
  border-radius: 9px;
  padding: 3px;
}
.period-toggle {
  min-width: 0;
  min-height: 30px;
  padding: 0;
  border-radius: 7px;
  border: none;
  box-shadow: none;
  opacity: 0.5;
}
.period-toggle label,
.period-toggle-label {
  font-size: 11px;
  font-weight: 700;
  padding: 7px 4px;
}
.period-toggle:checked {
  opacity: 1;
  background-image: linear-gradient(
    180deg,
    shade(@accent_bg_color, 1.1),
    @accent_bg_color
  );
  color: @accent_fg_color;
  box-shadow: 0 1px 3px alpha(@accent_bg_color, 0.28);
}
.period-toggle:disabled {
  opacity: 0.22;
}
.stock-status {
  font-size: 11px;
  margin-top: 6px;
}
.widget-window {
  background-color: transparent;
}
.widget-panel {
  background-image: linear-gradient(
    180deg,
    alpha(#ffffff, 0.07) 0%,
    alpha(#000000, 0.06) 100%
  );
  background-color: @window_bg_color;
  border-radius: 16px;
  border: 1px solid alpha(#ffffff, 0.08);
  box-shadow: 0 10px 36px alpha(#000000, 0.32);
}
.widget-drag-bar {
  min-height: 30px;
  padding: 0 4px 0 12px;
  background-image: linear-gradient(
    180deg,
    alpha(#ffffff, 0.05) 0%,
    transparent 100%
  );
  border-bottom: 1px solid alpha(#ffffff, 0.06);
}
.widget-drag-label {
  font-size: 11px;
  font-weight: 600;
  opacity: 0.5;
  letter-spacing: 0.03em;
  padding: 5px 0;
}
.widget-close-button {
  min-width: 26px;
  min-height: 26px;
  padding: 2px;
  border-radius: 999px;
  opacity: 0.55;
}
.widget-close-button:hover {
  opacity: 1;
  background-color: alpha(currentColor, 0.1);
}
"""


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _apply_css() -> None:
    display = Gdk.Display.get_default()
    if display is None:
        return
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(_CUSTOM_CSS)
    Gtk.StyleContext.add_provider_for_display(
        display,
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class StockDesktopApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._widget_desktop: WidgetDesktop | None = None

    def do_activate(self) -> None:  # noqa: N802 — convenção GObject
        _apply_css()
        config_manager = ConfigManager()
        config = config_manager.load()
        token = ConfigManager.load_token()
        if not token:
            logging.warning(
                "Token brapi não configurado. "
                "Defina BRAPI_TOKEN ou salve em ~/.config/stock-desktop/token"
            )
        apply_theme(config.theme)

        client = BrapiClient(token=token)
        service = StockService(client)

        default_period = (
            ChartPeriod.from_api_range(config.default_period) or ChartPeriod.ONE_DAY
        )

        if config.window_mode == "desktop_widget":
            logging.info("Iniciando em modo widget de desktop")
            self._widget_desktop = WidgetDesktop(
                self,
                service,
                config=config,
                config_manager=config_manager,
                default_period=default_period,
                client=client,
            )
            self._widget_desktop.present_all()
            return

        window = DashboardWindow(
            self,
            service,
            config=config,
            config_manager=config_manager,
            default_period=default_period,
            client=client,
        )
        window.present()


def main() -> int:
    _setup_logging()
    setup_application_icon()
    app = StockDesktopApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
