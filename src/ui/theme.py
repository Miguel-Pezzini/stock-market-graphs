from __future__ import annotations

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw


def apply_theme(theme: str) -> None:
    style_manager = Adw.StyleManager.get_default()
    if theme == "dark":
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    elif theme == "light":
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    else:
        style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
