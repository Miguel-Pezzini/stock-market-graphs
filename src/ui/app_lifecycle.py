from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk

logger = logging.getLogger(__name__)

_restart_pending = False


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _restart_argv() -> list[str]:
    if len(sys.argv) >= 2 and sys.argv[1] == "-m":
        return [sys.executable, *sys.argv[1:]]
    return [sys.executable, "-m", "src.main"]


def restart_application(application: Gtk.Application | Adw.Application) -> None:
    """Encerra o app e relança o processo principal."""
    global _restart_pending
    if _restart_pending:
        return
    _restart_pending = True

    root = _project_root()
    argv = _restart_argv()
    logger.info("Reiniciando aplicativo em %s", root)

    def _on_shutdown(_app: Gtk.Application | Adw.Application) -> None:
        try:
            os.chdir(root)
            os.execv(argv[0], argv)
        except OSError as exc:
            logger.error("Falha ao reiniciar aplicativo: %s", exc)
            _restart_pending = False

    application.connect("shutdown", _on_shutdown)
    application.quit()
