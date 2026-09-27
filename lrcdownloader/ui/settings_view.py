"""Settings tab: providers, skip policy, output, Spotify creds."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox,
                               QVBoxLayout, QWidget)

from lrcdownloader.config import Settings
from lrcdownloader.credentials import get_secret, set_secret


class SettingsView(QWidget):
    def __init__(self, cfg: Settings, log):
        super().__init__()
        self.cfg = cfg
        self.emit_log = log
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.synced_only = QCheckBox("Only accept synced lyrics")
        self.synced_only.setChecked(cfg.synced_only)
        form.addRow(self.synced_only)

        self.skip_sidecar = QCheckBox("Skip when sidecar .lrc exists (scan-first)")
        self.skip_sidecar.setChecked(cfg.skip_if_sidecar)
        form.addRow(self.skip_sidecar)

        self.embed_mode = QComboBox()
        self.embed_mode.addItems(["synced_or_better", "any", "none"])
        self.embed_mode.setCurrentText(cfg.embed_skip_mode)
        form.addRow("Embedded skip mode:", self.embed_mode)

        self.overwrite = QComboBox()
        self.overwrite.addItems(["missing", "never", "force"])
        self.overwrite.setCurrentText(cfg.overwrite)
        form.addRow("Overwrite:", self.overwrite)

        self.conc = QSpinBox()
        self.conc.setRange(1, 16)
        self.conc.setValue(cfg.concurrency)
        form.addRow("Concurrency:", self.conc)

        self.api_base = QLineEdit(cfg.spotify_api_base)
        form.addRow("Spotify API base:", self.api_base)
        self.sp_dc = QLineEdit(get_secret("SP_DC"))
        self.sp_dc.setEchoMode(QLineEdit.Password)
        self.sp_dc.setPlaceholderText("SP_DC cookie (opt-in, self-hosted API)")
        form.addRow("SP_DC:", self.sp_dc)
        self.cli_id = QLineEdit(get_secret("SPOTIFY_CLIENT_ID"))
        form.addRow("Spotify client ID:", self.cli_id)
        self.cli_sec = QLineEdit(get_secret("SPOTIFY_CLIENT_SECRET"))
        self.cli_sec.setEchoMode(QLineEdit.Password)
        form.addRow("Spotify client secret:", self.cli_sec)

        layout.addLayout(form)
        warn = QLabel(
            "Spotify path needs your own spotify-lyrics-api instance + SP_DC. "
            "It may violate Spotify TOS — disabled unless you configure it.")
        warn.setWordWrap(True)
        layout.addWidget(warn)
        row = QHBoxLayout()
        self.btn_save = QPushButton("Save settings")
        row.addWidget(self.btn_save)
        layout.addLayout(row)
        layout.addStretch(1)
        self.btn_save.clicked.connect(self.save)

    def save(self):
        self.cfg.synced_only = self.synced_only.isChecked()
        self.cfg.skip_if_sidecar = self.skip_sidecar.isChecked()
        self.cfg.embed_skip_mode = self.embed_mode.currentText()
        self.cfg.overwrite = self.overwrite.currentText()
        self.cfg.concurrency = self.conc.value()
        self.cfg.spotify_api_base = self.api_base.text().strip()
        self.cfg.save()
        set_secret("SP_DC", self.sp_dc.text().strip())
        set_secret("SPOTIFY_CLIENT_ID", self.cli_id.text().strip())
        set_secret("SPOTIFY_CLIENT_SECRET", self.cli_sec.text().strip())
        self.emit_log("Settings saved.")
