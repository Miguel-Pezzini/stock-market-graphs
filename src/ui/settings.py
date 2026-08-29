"""Janela de configurações do Stock Desktop."""

from __future__ import annotations

import re

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk

from src.api.brapi import BrapiClient
from src.config.config_manager import AppConfig, ConfigManager
from src.models.stock import ChartPeriod
from src.ui.app_icon import SETTINGS_ICON_NAME
from src.ui.app_lifecycle import restart_application
from src.ui.stock_refresh import StockRefreshCoordinator
from src.ui.theme import apply_theme

_THEME_LABELS = ("Sistema", "Claro", "Escuro")
_THEME_VALUES = ("system", "light", "dark")

_WINDOW_MODE_LABELS = ("Janela normal", "Widget de desktop")
_WINDOW_MODE_VALUES = ("normal", "desktop_widget")

_API_PLAN_LABELS = ("Gratuito", "Pago")
_API_PLAN_VALUES = ("free", "paid")

_PERIOD_LABELS = tuple(period.label for period in ChartPeriod)
_PERIOD_VALUES = tuple(period.range for period in ChartPeriod)


def parse_stocks(text: str) -> list[str]:
    parts = re.split(r"[\s,;]+", text.strip())
    return [part.upper() for part in parts if part.strip()]


class SettingsWindow(Adw.ApplicationWindow):
    """Preferências editáveis com persistência em config.json e token."""

    def __init__(
        self,
        parent: Gtk.Window,
        config: AppConfig,
        config_manager: ConfigManager,
        *,
        client: BrapiClient | None = None,
        coordinator: StockRefreshCoordinator | None = None,
    ) -> None:
        application = parent.get_application()
        super().__init__(application=application, title="Configurações")
        self._application = application
        self._parent = parent
        self._config = config
        self._config_manager = config_manager
        self._client = client
        self._coordinator = coordinator
        self._original = self._snapshot(config)

        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(520, 720)

        header = Adw.HeaderBar()
        save_button = Gtk.Button(label="Salvar")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save_clicked)
        header.pack_end(save_button)

        restart_button = Gtk.Button(label="Reiniciar")
        restart_button.set_tooltip_text("Reiniciar o aplicativo")
        restart_button.connect("clicked", self._on_restart_clicked)
        header.pack_end(restart_button)

        page = Adw.PreferencesPage()
        page.set_title("Configurações")
        page.set_icon_name(SETTINGS_ICON_NAME)
        page.add(self._build_api_group())
        page.add(self._build_stocks_group())
        page.add(self._build_display_group())
        page.add(self._build_refresh_group())
        page.add(self._build_layout_group())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(page)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(header)
        root.append(scrolled)
        self.set_content(root)

    @staticmethod
    def _snapshot(config: AppConfig) -> dict[str, object]:
        return {
            "stocks": list(config.stocks),
            "theme": config.theme,
            "window_mode": config.window_mode,
            "api_plan": config.api_plan,
            "default_period": config.default_period,
            "columns": config.columns,
            "refresh_interval": config.refresh_interval,
            "window_width": config.window_width,
            "window_height": config.window_height,
            "card_width": config.card_width,
            "card_height": config.card_height,
        }

    def _build_api_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title("API brapi.dev")
        if ConfigManager.has_saved_token():
            group.set_description(
                "Token em brapi.dev/dashboard. Deixe o campo vazio para manter o atual."
            )
        else:
            group.set_description("Cole seu token gratuito de brapi.dev/dashboard")

        self._token_row = Adw.PasswordEntryRow(title="Token")
        group.add(self._token_row)

        self._api_plan_row = Adw.ComboRow(title="Plano da API")
        self._api_plan_row.set_model(Gtk.StringList.new(list(_API_PLAN_LABELS)))
        self._api_plan_row.set_selected(_API_PLAN_VALUES.index(self._config.api_plan))
        group.add(self._api_plan_row)

        return group

    def _build_stocks_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title("Ações monitoradas")
        group.set_description("Um ticker por linha ou separados por vírgula")

        frame = Gtk.Frame()
        frame.add_css_class("card")
        frame.set_margin_top(6)
        frame.set_margin_bottom(6)
        frame.set_margin_start(12)
        frame.set_margin_end(12)

        self._stocks_buffer = Gtk.TextBuffer()
        self._stocks_buffer.set_text("\n".join(self._config.stocks))

        text_view = Gtk.TextView(buffer=self._stocks_buffer)
        text_view.set_monospace(True)
        text_view.set_left_margin(8)
        text_view.set_right_margin(8)
        text_view.set_top_margin(8)
        text_view.set_bottom_margin(8)
        text_view.set_vexpand(True)
        text_view.set_size_request(-1, 120)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(120)
        scrolled.set_child(text_view)
        frame.set_child(scrolled)

        group.add(frame)
        return group

    def _build_display_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title("Exibição")

        self._theme_row = Adw.ComboRow(title="Tema")
        self._theme_row.set_model(Gtk.StringList.new(list(_THEME_LABELS)))
        self._theme_row.set_selected(_THEME_VALUES.index(self._config.theme))
        group.add(self._theme_row)

        self._window_mode_row = Adw.ComboRow(title="Modo de janela")
        self._window_mode_row.set_model(Gtk.StringList.new(list(_WINDOW_MODE_LABELS)))
        self._window_mode_row.set_selected(
            _WINDOW_MODE_VALUES.index(self._config.window_mode)
        )
        group.add(self._window_mode_row)

        self._default_period_row = Adw.ComboRow(title="Período padrão")
        self._default_period_row.set_model(Gtk.StringList.new(list(_PERIOD_LABELS)))
        default_index = (
            _PERIOD_VALUES.index(self._config.default_period)
            if self._config.default_period in _PERIOD_VALUES
            else 0
        )
        self._default_period_row.set_selected(default_index)
        group.add(self._default_period_row)

        return group

    def _build_refresh_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title("Atualização")

        self._refresh_row = Adw.SpinRow(title="Intervalo de cotações")
        adjustment = Gtk.Adjustment.new(
            self._config.refresh_interval,
            60,
            86_400,
            60,
            300,
            0,
        )
        self._refresh_row.set_adjustment(adjustment)
        self._refresh_row.set_subtitle("Em segundos (mínimo 60)")
        group.add(self._refresh_row)

        return group

    def _build_layout_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title("Layout")
        group.set_description("Tamanho fixo da janela; os cards se ajustam ao espaço disponível")

        self._window_width_row = Adw.SpinRow(title="Largura da janela")
        self._window_width_row.set_adjustment(
            Gtk.Adjustment.new(self._config.window_width, 560, 1200, 10, 40, 0)
        )
        self._window_width_row.set_subtitle("Em pixels")
        group.add(self._window_width_row)

        self._window_height_row = Adw.SpinRow(title="Altura da janela")
        self._window_height_row.set_adjustment(
            Gtk.Adjustment.new(self._config.window_height, 320, 900, 10, 40, 0)
        )
        self._window_height_row.set_subtitle("Em pixels")
        group.add(self._window_height_row)

        self._columns_row = Adw.SpinRow(title="Colunas")
        self._columns_row.set_adjustment(
            Gtk.Adjustment.new(self._config.columns, 1, 6, 1, 1, 0)
        )
        group.add(self._columns_row)

        self._card_width_row = Adw.SpinRow(title="Largura do card")
        self._card_width_row.set_adjustment(
            Gtk.Adjustment.new(self._config.card_width, 260, 320, 4, 8, 0)
        )
        self._card_width_row.set_subtitle("Largura de cada card no painel widget")
        group.add(self._card_width_row)

        self._card_height_row = Adw.SpinRow(title="Altura do card")
        self._card_height_row.set_adjustment(
            Gtk.Adjustment.new(self._config.card_height, 195, 240, 4, 4, 0)
        )
        self._card_height_row.set_subtitle("Altura fixa de cada card compacto")
        group.add(self._card_height_row)

        return group

    def _collect_config(self) -> AppConfig:
        start, end = self._stocks_buffer.get_bounds()
        stocks_text = self._stocks_buffer.get_text(start, end, False)
        stocks = parse_stocks(stocks_text)

        self._config.stocks = stocks or self._config.stocks
        self._config.theme = _THEME_VALUES[self._theme_row.get_selected()]
        self._config.window_mode = _WINDOW_MODE_VALUES[self._window_mode_row.get_selected()]
        self._config.api_plan = _API_PLAN_VALUES[self._api_plan_row.get_selected()]
        self._config.default_period = _PERIOD_VALUES[self._default_period_row.get_selected()]
        self._config.refresh_interval = int(self._refresh_row.get_value())
        self._config.columns = int(self._columns_row.get_value())
        self._config.window_width = int(self._window_width_row.get_value())
        self._config.window_height = int(self._window_height_row.get_value())
        self._config.card_width = int(self._card_width_row.get_value())
        self._config.card_height = int(self._card_height_row.get_value())
        return self._config_manager.normalize(self._config)

    def _requires_restart(self, updated: AppConfig) -> bool:
        current = self._snapshot(updated)
        restart_keys = (
            "stocks",
            "window_mode",
            "api_plan",
            "columns",
            "window_width",
            "window_height",
            "card_width",
            "card_height",
        )
        return any(self._original[key] != current[key] for key in restart_keys)

    def _on_restart_clicked(self, *_args: object) -> None:
        if self._application is None:
            return
        restart_application(self._application)

    def _on_save_clicked(self, *_args: object) -> None:
        updated = self._collect_config()
        self._config_manager.save(updated)

        token_text = self._token_row.get_text().strip()
        if token_text:
            ConfigManager.save_token(token_text)
            if self._client is not None:
                self._client.set_token(token_text)

        apply_theme(updated.theme)

        if self._coordinator is not None:
            self._coordinator.set_refresh_interval(updated.refresh_interval)

        requires_restart = self._requires_restart(updated)
        if requires_restart:
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Configurações salvas",
                body=(
                    "Algumas alterações (ações, layout ou modo de janela) "
                    "só entram em vigor após reiniciar o aplicativo."
                ),
            )
            dialog.add_response("restart", "Reiniciar agora")
            dialog.add_response("ok", "Depois")
            dialog.set_default_response("restart")
            dialog.set_close_response("ok")

            def _on_dialog_response(_dialog: Adw.MessageDialog, response: str) -> None:
                if response == "restart" and self._application is not None:
                    restart_application(self._application)
                else:
                    self.close()

            dialog.connect("response", _on_dialog_response)
            dialog.present()
        else:
            self.close()


def open_settings(
    parent: Gtk.Window,
    config: AppConfig,
    config_manager: ConfigManager,
    *,
    client: BrapiClient | None = None,
    coordinator: StockRefreshCoordinator | None = None,
    existing: SettingsWindow | None = None,
) -> SettingsWindow:
    """Abre ou foca a janela de configurações."""
    if existing is not None and existing.get_visible():
        existing.present()
        return existing

    window = SettingsWindow(
        parent,
        config,
        config_manager,
        client=client,
        coordinator=coordinator,
    )
    window.present()
    return window
