"""Main window: Library / Search / Settings tabs + log pane."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from lrcdownloader.config import Settings
from lrcdownloader.ui.library_view import LibraryView
from lrcdownloader.ui.search_view import SearchView
from lrcdownloader.ui.settings_view import SettingsView


class MainWindow(QMainWindow):
    def __init__(self, cfg: Settings):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("LRC Downloader")
        self.resize(1000, 700)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.log_view = QTextEdit(readOnly=True)
        self.log_view.setMaximumHeight(140)
        layout.addWidget(self.log_view)

        self.library = LibraryView(cfg)
        self.search = SearchView(cfg, self.log)
        self.settings = SettingsView(cfg, self.log)
        self.tabs.addTab(self.library, "Library")
        self.tabs.addTab(self.search, "Manual search")
        self.tabs.addTab(self.settings, "Settings")
        self.library.log.connect(self.log)

    def log(self, msg: str):
        self.log_view.append(msg)
