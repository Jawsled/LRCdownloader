"""Qt entry point."""
from __future__ import annotations

import sys

from lrcdownloader.config import get_settings


def main() -> None:
    from PySide6.QtWidgets import QApplication

    from lrcdownloader.ui.main_window import MainWindow

    cfg = get_settings()
    app = QApplication(sys.argv)
    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec())
