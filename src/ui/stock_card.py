from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango

from src.charts.stock_chart import StockChart
from src.models.stock import (
    FREE_PLAN_TOOLTIP,
    ChartPeriod,
    StockHistory,
    StockQuote,
)


class StockCard(Gtk.Box):
    """Card com cotação, gráfico histórico e seleção de período."""

    def __init__(
        self,
        symbol: str,
        default_period: ChartPeriod = ChartPeriod.ONE_DAY,
        on_period_changed: Callable[[str, ChartPeriod], None] | None = None,
        allowed_periods: frozenset[ChartPeriod] | None = None,
        *,
        compact: bool = False,
        use_window_handle: bool = False,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._symbol = symbol.upper()
        self._allowed_periods = allowed_periods or frozenset(ChartPeriod)
        if default_period not in self._allowed_periods:
            default_period = ChartPeriod.ONE_DAY
        self._period = default_period
        self._on_period_changed = on_period_changed
        self._positive: bool | None = None
        self._history_closes: list[float] = []
        self._live_price: float | None = None
        self._day_open: float | None = None
        self._day_high: float | None = None
        self._day_low: float | None = None
        self._use_window_handle = use_window_handle

        self.add_css_class("stock-card")
        if compact:
            self.add_css_class("compact")
            self.set_valign(Gtk.Align.FILL)
            self.set_vexpand(True)
        else:
            self.set_valign(Gtk.Align.FILL)
        self.set_halign(Gtk.Align.FILL)
        if not compact:
            self.set_overflow(Gtk.Overflow.HIDDEN)

        self._header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._header.add_css_class("card-header")
        self._header.set_vexpand(False)
        if compact:
            self._header.set_size_request(-1, 26)
        if use_window_handle:
            self._drag_area: Gtk.Widget = Gtk.WindowHandle()
            self._drag_area.set_child(self._header)
            self._drag_area.add_css_class("card-drag-handle")
            self.append(self._drag_area)
        else:
            self._drag_area = self._header
            self.append(self._header)

        self._ticker_label = Gtk.Label(label=self._symbol)
        self._ticker_label.add_css_class("stock-ticker")
        self._ticker_label.set_halign(Gtk.Align.START)
        self._ticker_label.set_valign(Gtk.Align.CENTER)
        self._ticker_label.set_hexpand(True)
        self._ticker_label.set_margin_top(2)
        self._ticker_label.set_margin_bottom(2)
        self._header.append(self._ticker_label)

        self._change_badge = Gtk.Box()
        self._change_badge.add_css_class("change-badge")
        self._change_badge.set_halign(Gtk.Align.END)
        self._change_badge.set_valign(Gtk.Align.CENTER)
        self._change_label = Gtk.Label(label="—")
        self._change_label.add_css_class("stock-change")
        self._change_badge.append(self._change_label)
        self._header.append(self._change_badge)

        self._name_label = Gtk.Label()
        self._name_label.add_css_class("stock-name")
        self._name_label.set_halign(Gtk.Align.START)
        self._name_label.set_xalign(0)
        self._name_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._name_label.set_visible(False)
        self.append(self._name_label)

        self._price_label = Gtk.Label(label="Carregando…")
        self._price_label.add_css_class("stock-price")
        self._price_label.set_halign(Gtk.Align.START)
        self._price_label.set_xalign(0)
        self._price_label.set_vexpand(False)
        self.append(self._price_label)

        self._chart = StockChart(expand=False, compact=compact)
        self._chart.add_css_class("chart-area")
        self._chart.set_vexpand(False)
        self.append(self._chart)

        self._bottom_spacer = Gtk.Box()
        self._bottom_spacer.set_vexpand(compact)
        self._bottom_spacer.set_hexpand(True)
        if compact:
            self.append(self._bottom_spacer)

        self._period_bar = Gtk.Box(spacing=2, homogeneous=True)
        self._period_bar.add_css_class("period-bar")
        self._period_bar.set_halign(Gtk.Align.FILL)
        self._period_bar.set_vexpand(False)
        self._period_bar.set_valign(Gtk.Align.END)
        self._period_toggles: dict[ChartPeriod, Gtk.ToggleButton] = {}

        for period in ChartPeriod:
            toggle = Gtk.ToggleButton()
            toggle.add_css_class("period-toggle")
            period_label = Gtk.Label(label=period.label)
            period_label.add_css_class("period-toggle-label")
            period_label.set_valign(Gtk.Align.CENTER)
            period_label.set_halign(Gtk.Align.CENTER)
            toggle.set_child(period_label)
            toggle.set_hexpand(True)
            toggle.set_halign(Gtk.Align.FILL)
            toggle.set_valign(Gtk.Align.CENTER)
            toggle.set_vexpand(False)
            if period in self._allowed_periods:
                toggle.set_tooltip_text(f"Variação no período {period.label}")
            else:
                toggle.set_sensitive(False)
                toggle.set_tooltip_text(FREE_PLAN_TOOLTIP)
            toggle.connect("toggled", self._on_period_toggled, period)
            self._period_bar.append(toggle)
            self._period_toggles[period] = toggle
            if period is default_period:
                toggle.set_active(True)

        self.append(self._period_bar)

        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("dim-label")
        self._status_label.add_css_class("stock-status")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_wrap(True)
        self._status_label.set_vexpand(False)
        self._status_label.set_visible(False)
        self.append(self._status_label)

    @property
    def period(self) -> ChartPeriod:
        return self._period

    @property
    def uses_native_drag(self) -> bool:
        """True quando o arraste usa Gtk.WindowHandle (Wayland/X11 nativo)."""
        return self._use_window_handle

    @property
    def drag_handle(self) -> Gtk.Widget:
        """Área arrastável (cabeçalho do card) para modo widget."""
        return self._drag_area

    def _set_status(self, message: str) -> None:
        if message:
            self._status_label.set_text(message)
            self._status_label.set_visible(True)
        else:
            self._status_label.set_text("")
            self._status_label.set_visible(False)

    def _set_long_name(self, long_name: str | None) -> None:
        if long_name:
            self._name_label.set_text(long_name)
            self._name_label.set_tooltip_text(long_name)
            self._name_label.set_visible(True)
        else:
            self._name_label.set_text("")
            self._name_label.set_tooltip_text(None)
            self._name_label.set_visible(False)

    def _chart_closes(self) -> list[float]:
        closes = self._history_closes
        if self._period is ChartPeriod.ONE_DAY and len(closes) <= 1:
            synthetic = self._synthesize_day_closes()
            if synthetic:
                return synthetic
        return closes

    def _synthesize_day_closes(self) -> list[float] | None:
        if self._live_price is None or self._day_open is None:
            return None

        open_price = self._day_open
        close = self._live_price
        high = self._day_high if self._day_high is not None else max(open_price, close)
        low = self._day_low if self._day_low is not None else min(open_price, close)

        if close >= open_price:
            return [open_price, low, high, close]
        return [open_price, high, low, close]

    def _apply_period_values(self) -> None:
        """Atualiza preço e variação com base no período selecionado."""
        closes = self._chart_closes()
        if not closes:
            return

        start_price = closes[0]
        end_price = self._live_price if self._live_price is not None else closes[-1]
        self._price_label.set_text(self._format_price(end_price))

        if start_price != 0:
            change_pct = ((end_price - start_price) / start_price) * 100
            self._change_label.set_text(self._format_change(change_pct))
            self._apply_change_style(change_pct)
            self._positive = change_pct >= 0
        else:
            self._change_label.set_text("0,00%")
            self._apply_change_style(0.0)
            self._positive = True

        self._set_status("")
        self._chart.update(closes, positive=self._positive)

    def _store_quote_day_fields(self, quote: StockQuote) -> None:
        self._day_open = quote.market_open
        self._day_high = quote.day_high
        self._day_low = quote.day_low

    def update_quote(self, quote: StockQuote) -> None:
        if quote.error or quote.price is None:
            if self._history_closes:
                self._apply_period_values()
                return

            self._live_price = None
            self._price_label.set_text("—")
            self._change_label.set_text("—")
            self._apply_change_style(None)
            self._set_status(quote.error or "Sem dados disponíveis")
            self._positive = None
            return

        self._live_price = quote.price
        self._store_quote_day_fields(quote)

        self._set_long_name(quote.long_name)

        if self._history_closes:
            self._apply_period_values()
        else:
            self._price_label.set_text(self._format_price(quote.price))
            self._change_label.set_text(self._format_change(quote.change_percent))
            self._apply_change_style(quote.change_percent)
            self._positive = quote.is_positive
            self._set_status("")

    def update_history(self, history: StockHistory) -> None:
        if history.error or not history.has_data:
            if self._period is ChartPeriod.ONE_DAY and self._synthesize_day_closes():
                self._history_closes = []
                self._apply_period_values()
                return

            self._history_closes = []
            self._chart.clear()
            self._set_status(history.error or "Histórico indisponível")
            return

        self._history_closes = history.closes
        self._apply_period_values()

    def _on_period_toggled(self, button: Gtk.ToggleButton, period: ChartPeriod) -> None:
        if period not in self._allowed_periods:
            button.set_active(False)
            return

        if not button.get_active():
            if not any(t.get_active() for t in self._period_toggles.values()):
                button.set_active(True)
            return

        for other_period, toggle in self._period_toggles.items():
            if other_period is not period and toggle.get_active():
                toggle.set_active(False)

        if period is self._period:
            return

        self._period = period
        self._set_status("Atualizando gráfico…")
        if self._on_period_changed:
            self._on_period_changed(self._symbol, period)

    @staticmethod
    def _format_price(price: float) -> str:
        return f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_change(change_percent: float | None) -> str:
        if change_percent is None:
            return "—"
        sign = "+" if change_percent >= 0 else ""
        return f"{sign}{change_percent:.2f}%"

    def _apply_change_style(self, change_percent: float | None) -> None:
        for widget in (self._change_label, self._change_badge):
            widget.remove_css_class("success")
            widget.remove_css_class("error")
            widget.remove_css_class("neutral")
        if change_percent is None:
            self._change_badge.add_css_class("neutral")
            return
        css_class = "success" if change_percent >= 0 else "error"
        self._change_label.add_css_class(css_class)
        self._change_badge.add_css_class(css_class)
