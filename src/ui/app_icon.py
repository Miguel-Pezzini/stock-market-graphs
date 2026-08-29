from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

APP_ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "app-icon.svg"
APP_ICON_NAME = "com.stockdesktop.app"

_SETTINGS_ICON_NAME = "emblem-system-symbolic"
SETTINGS_ICON_NAME = _SETTINGS_ICON_NAME

_PROJECT_ROOT = APP_ICON_PATH.parents[1]
_ICONS_SEARCH_PATH = _PROJECT_ROOT / "share" / "icons"
_USER_ICONS_PATH = Path.home() / ".local/share/icons/hicolor/scalable/apps"
_ICON_THEME_PATH = (
    _ICONS_SEARCH_PATH / "hicolor" / "scalable" / "apps" / f"{APP_ICON_NAME}.svg"
)
_USER_ICON_PATH = _USER_ICONS_PATH / f"{APP_ICON_NAME}.svg"
_icon_setup_done = False


def _ensure_icon_in_theme() -> None:
    global _icon_setup_done
    if _icon_setup_done:
        return

    _ICON_THEME_PATH.parent.mkdir(parents=True, exist_ok=True)
    _USER_ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    source = APP_ICON_PATH.read_text(encoding="utf-8")
    for destination in (_ICON_THEME_PATH, _USER_ICON_PATH):
        if not destination.exists() or destination.read_text(encoding="utf-8") != source:
            destination.write_text(source, encoding="utf-8")

    display = Gdk.Display.get_default()
    if display is not None:
        theme = Gtk.IconTheme.get_for_display(display)
        for search_path in (
            str(_ICONS_SEARCH_PATH),
            str(_USER_ICON_PATH.parents[3]),
        ):
            if search_path not in theme.get_search_path():
                theme.add_search_path(search_path)

    Gtk.Window.set_default_icon_name(APP_ICON_NAME)
    _icon_setup_done = True


def setup_application_icon() -> None:
    """Registra o ícone do app no tema local e define o padrão das janelas."""
    _ensure_icon_in_theme()


def apply_window_icon(window: Gtk.Window) -> None:
    _ensure_icon_in_theme()
    window.set_icon_name(APP_ICON_NAME)


def make_app_icon_image(*, pixel_size: int = 16) -> Gtk.Image:
    image = Gtk.Image.new_from_file(str(APP_ICON_PATH))
    image.set_pixel_size(pixel_size)
    return image


def make_title_widget(label: str = "Stock Desktop") -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box.append(make_app_icon_image(pixel_size=20))
    box.append(Gtk.Label(label=label))
    return box


def make_settings_button() -> Gtk.Button:
    button = Gtk.Button(icon_name=_SETTINGS_ICON_NAME)
    button.set_tooltip_text("Configurações")
    return button
