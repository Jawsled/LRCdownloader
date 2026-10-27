"""Settings tab: providers, skip policy, output, Spotify creds."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from lrcdownloader.config import KNOWN_PROVIDERS, Settings
from lrcdownloader.credentials import get_secret, set_secret

PROVIDER_LABELS = {
    "lrclib": "LRCLIB (default, no key)",
    "lrcred": "lrc.red (free, no key)",
    "netease": "NetEase Cloud Music (unofficial)",
    "qq": "QQ Music (unofficial)",
    "syncedlyrics": "syncedlyrics (Musixmatch/Megalobiz/...)",
    "spotify": "Spotify (opt-in, needs SP_DC)",
}


def _ordered_providers(order: list[str]) -> list[str]:
    known = [p for p in order if p in KNOWN_PROVIDERS]
    return known + [p for p in KNOWN_PROVIDERS if p not in known]


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

        self.providers = QListWidget()
        self.providers.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.providers.setMinimumHeight(130)
        self.providers.setMaximumHeight(170)
        for p in _ordered_providers(cfg.provider_order):
            item = QListWidgetItem(PROVIDER_LABELS.get(p, p))
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if p in cfg.provider_order
                else Qt.CheckState.Unchecked
            )
            self.providers.addItem(item)

        pbox = QWidget()
        pbox_layout = QVBoxLayout(pbox)
        pbox_layout.setContentsMargins(0, 0, 0, 0)
        pbox_layout.addWidget(self.providers)
        prow = QHBoxLayout()
        self.btn_up = QPushButton("Move up")
        self.btn_down = QPushButton("Move down")
        prow.addWidget(self.btn_up)
        prow.addWidget(self.btn_down)
        prow.addStretch(1)
        pbox_layout.addLayout(prow)
        form.addRow("Provider fallback order:", pbox)

        self.lrcred_contact = QLineEdit(cfg.lrcred_contact)
        self.lrcred_contact.setPlaceholderText("Required for lrc.red; you'll be prompted if empty")
        form.addRow("lrc.red contact email:", self.lrcred_contact)

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
        note = QLabel(
            "Providers are tried top-to-bottom. Untick one to disable it. "
            'lrc.red asks apps to identify themselves and to credit '
            '<a href="https://lrc.red">lrc.red</a>; '
            "NetEase/QQ use unofficial web APIs and may be rate-limited.")
        note.setWordWrap(True)
        note.setOpenExternalLinks(True)
        layout.addWidget(note)
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
        self.btn_up.clicked.connect(lambda: self._move_provider(-1))
        self.btn_down.clicked.connect(lambda: self._move_provider(1))

    def _move_provider(self, delta: int):
        row = self.providers.currentRow()
        new_row = row + delta
        if row < 0 or not (0 <= new_row < self.providers.count()):
            return
        item = self.providers.takeItem(row)
        self.providers.insertItem(new_row, item)
        self.providers.setCurrentRow(new_row)

    def save(self):
        self.cfg.synced_only = self.synced_only.isChecked()
        self.cfg.skip_if_sidecar = self.skip_sidecar.isChecked()
        self.cfg.embed_skip_mode = self.embed_mode.currentText()
        self.cfg.overwrite = self.overwrite.currentText()
        self.cfg.concurrency = self.conc.value()
        self.cfg.provider_order = [
            self.providers.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.providers.count())
            if self.providers.item(i).checkState() == Qt.CheckState.Checked
        ]
        self.cfg.lrcred_contact = self.lrcred_contact.text().strip()
        self.cfg.spotify_api_base = self.api_base.text().strip()
        self.cfg.save()
        set_secret("SP_DC", self.sp_dc.text().strip())
        set_secret("SPOTIFY_CLIENT_ID", self.cli_id.text().strip())
        set_secret("SPOTIFY_CLIENT_SECRET", self.cli_sec.text().strip())
        self.emit_log("Settings saved.")
