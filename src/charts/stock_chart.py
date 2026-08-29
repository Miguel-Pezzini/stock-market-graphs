from __future__ import annotations

import io
import logging

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

_POSITIVE_COLOR = "#2ec27e"
_NEGATIVE_COLOR = "#e01b24"
CHART_HEIGHT = 80
CHART_HEIGHT_COMPACT = 56


class StockChart(Gtk.Box):
    """Gráfico de linha minimalista embutido no card.

    Renderiza off-screen via backend Agg e exibe como Gdk.Texture no Gtk.Picture,
    evitando a dependência python3-gi-cairo exigida pelo backend GTK4Agg.
    """

    def __init__(self, *, expand: bool = False, compact: bool = False) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._expand = expand
        self._min_height = CHART_HEIGHT_COMPACT if compact else CHART_HEIGHT
        self.set_vexpand(expand)
        self.set_hexpand(True)
        self.set_overflow(Gtk.Overflow.HIDDEN)

        self._figure = Figure(figsize=(3.2, 1.0), dpi=100)
        self._figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self._figure.patch.set_alpha(0)
        self._axes = self._figure.add_subplot(111)
        self._axes.set_axis_off()
        self._canvas = FigureCanvasAgg(self._figure)

        self._picture = Gtk.Picture()
        self._picture.set_content_fit(Gtk.ContentFit.FILL)
        self._picture.set_can_shrink(True)
        self._picture.set_vexpand(expand)
        self._picture.set_hexpand(True)
        self._picture.set_overflow(Gtk.Overflow.HIDDEN)
        if not expand:
            self._picture.set_size_request(-1, self._min_height)
        else:
            self._picture.set_size_request(-1, self._min_height)
        self.append(self._picture)

        self.connect("notify::width", self._on_size_changed)
        self.connect("notify::height", self._on_size_changed)

    def _chart_height(self) -> int:
        height = self.get_height() if self._expand else self._min_height
        return max(height, self._min_height)

    def _on_size_changed(self, *_args: object) -> None:
        width = self.get_width()
        if width <= 0:
            return
        dpi = self._figure.get_dpi()
        self._figure.set_size_inches(width / dpi, self._chart_height() / dpi, forward=True)

    def update(self, closes: list[float], positive: bool | None = None) -> None:
        self._axes.clear()
        self._axes.set_axis_off()

        if not closes:
            self._picture.set_paintable(None)
            return

        if positive is None and len(closes) >= 2:
            positive = closes[-1] >= closes[0]
        elif positive is None:
            positive = True

        color = _POSITIVE_COLOR if positive else _NEGATIVE_COLOR
        self._axes.plot(closes, color=color, linewidth=2.0, solid_capstyle="round")

        ymin = min(closes)
        ymax = max(closes)
        padding = (ymax - ymin) * 0.08 or max(abs(ymax) * 0.01, 0.05)
        self._axes.set_xlim(-0.5, len(closes) - 0.5)
        self._axes.set_ylim(ymin - padding, ymax + padding)

        self._render_to_picture()

    def clear(self) -> None:
        self.update([])

    def _render_to_picture(self) -> None:
        width = max(self.get_width(), 160)
        height = self._chart_height()
        dpi = self._figure.get_dpi()
        self._figure.set_size_inches(width / dpi, height / dpi, forward=True)

        buffer = io.BytesIO()
        self._figure.savefig(
            buffer,
            format="png",
            transparent=True,
            pad_inches=0,
        )
        texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(buffer.getvalue()))
        self._picture.set_paintable(texture)
