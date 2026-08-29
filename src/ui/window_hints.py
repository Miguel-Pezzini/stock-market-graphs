from __future__ import annotations

import logging

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

logger = logging.getLogger(__name__)

_wayland_hint_logged = False


def is_wayland() -> bool:
    display = Gdk.Display.get_default()
    if display is None:
        return True
    return "x11" not in display.get_name().lower()


def apply_desktop_widget_hints(window: Gtk.Window) -> None:
    """Melhor esforço para janelas discretas no desktop (X11/XWayland).

    No GNOME Wayland puro, o compositor ignora a maioria desses hints.
    """
    surface = window.get_surface()
    if surface is None:
        return

    display = Gdk.Display.get_default()
    if display is None:
        return

    display_name = display.get_name().lower()
    if "x11" not in display_name:
        global _wayland_hint_logged
        if not _wayland_hint_logged:
            _wayland_hint_logged = True
            logger.info(
                "Modo widget: hints de desktop limitados no Wayland (GNOME). "
                "Widgets aparecem como janelas frameless posicionáveis."
            )
        return

    try:
        gi.require_version("GdkX11", "4.0")
        from gi.repository import GdkX11

        x11_surface = GdkX11.X11Surface.from_surface(surface)
        x11_surface.set_skip_taskbar_hint(True)
        x11_surface.set_skip_pager_hint(True)
        if hasattr(x11_surface, "set_keep_below"):
            x11_surface.set_keep_below(True)
        logger.debug("Hints X11 de widget aplicados")
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        logger.debug("Não foi possível aplicar hints X11: %s", exc)


def move_window(window: Gtk.Window, x: int, y: int) -> bool:
    surface = window.get_surface()
    if surface is None:
        return False
    try:
        surface.move(int(x), int(y))
        return True
    except (AttributeError, TypeError):
        return False


def get_window_origin(window: Gtk.Window) -> tuple[int, int] | None:
    surface = window.get_surface()
    if surface is None:
        return None
    try:
        origin = surface.get_origin()
        if origin is None:
            return None
        return int(origin[0]), int(origin[1])
    except (AttributeError, TypeError, ValueError):
        return None
