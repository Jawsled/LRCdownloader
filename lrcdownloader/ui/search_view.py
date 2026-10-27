"""Manual search tab: query providers, preview, save .lrc."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QListWidget,
                               QPushButton, QTextEdit, QVBoxLayout, QWidget,
                               QLineEdit)

from lrcdownloader.config import Settings
from lrcdownloader.core.batch import build_providers
from lrcdownloader.core.providers.base import LrcResult
from lrcdownloader.ui.lrcred_prompt import ensure_lrcred_contact


class SearchView(QWidget):
    def __init__(self, cfg: Settings, log):
        super().__init__()
        self.cfg = cfg
        self.emit_log = log
        self.cands: list[LrcResult] = []
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Artist - Title  (e.g. Daft Punk - Get Lucky)")
        self.btn = QPushButton("Search")
        row.addWidget(self.q, 1)
        row.addWidget(self.btn)
        layout.addLayout(row)
        mid = QHBoxLayout()
        self.list = QListWidget()
        self.preview = QTextEdit(readOnly=True)
        mid.addWidget(self.list, 1)
        mid.addWidget(self.preview, 2)
        layout.addLayout(mid)
        brow = QHBoxLayout()
        self.btn_save = QPushButton("Save .lrc as…")
        brow.addWidget(QLabel("Pick a candidate, preview, then save."))
        brow.addWidget(self.btn_save)
        layout.addLayout(brow)
        self.btn.clicked.connect(self.search)
        self.list.currentRowChanged.connect(self.show)
        self.btn_save.clicked.connect(self.save)

    def search(self):
        query = self.q.text().strip()
        if not query:
            return
        self.cands = []
        if "lrcred" in self.cfg.provider_order and not ensure_lrcred_contact(self, self.cfg):
            self.emit_log("lrc.red skipped: no contact email set.")
        if " - " in query:
            artist, title = [s.strip() for s in query.split(" - ", 1)]
        else:
            title, artist = query, ""
        for p in build_providers(self.cfg):
            try:
                found = p.search_text(query)
                if not found:
                    r = p.search(title, artist)
                    found = [r] if r else []
                self.cands.extend(found)
            except Exception as e:  # noqa: BLE001
                self.emit_log(f"{p.name} search failed: {e}")
        self.cands.sort(key=lambda r: (r.synced, r.score), reverse=True)
        self.list.clear()
        for c in self.cands:
            self.list.addItem(f"[{c.kind}] {c.source}  ({len(c.lrc_text.splitlines())} lines)")
        self.emit_log(f"Manual search: {len(self.cands)} candidate(s).")
        if self.cands:
            self.list.setCurrentRow(0)

    def show(self, i: int):
        if 0 <= i < len(self.cands):
            self.preview.setPlainText(self.cands[i].lrc_text)

    def save(self):
        i = self.list.currentRow()
        if not (0 <= i < len(self.cands)):
            return
        fn, _ = QFileDialog.getSaveFileName(self, "Save lyrics", filter="Lyrics (*.lrc)")
        if fn:
            p = Path(fn).with_suffix(".lrc")
            p.write_text(self.cands[i].lrc_text, encoding="utf-8")
            self.emit_log(f"Saved {p}")
