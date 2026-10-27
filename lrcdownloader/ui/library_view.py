"""Library tab: folder pick, drag&drop import, scan table, batch run."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from lrcdownloader.config import Settings
from lrcdownloader.core.batch import BatchRunner
from lrcdownloader.core.metadata import SUPPORTED_SUFFIXES
from lrcdownloader.core.scanner import SongRecord, scan_sources
from lrcdownloader.ui.lrcred_prompt import ensure_lrcred_contact


class Worker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list)

    def __init__(self, records: list[SongRecord], cfg: Settings):
        super().__init__()
        self.records = records
        self.cfg = cfg
        self.runner = BatchRunner(cfg)

    def run(self):
        outcomes = self.runner.run(self.records, on_progress=self.progress.emit)
        self.finished.emit(outcomes)


class LibraryView(QWidget):
    log = Signal(str)

    def __init__(self, cfg: Settings):
        super().__init__()
        self.cfg = cfg
        self.records: list[SongRecord] = []
        self.sources: list[Path] = []
        self.worker: Worker | None = None

        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_folder = QPushButton("Choose folder…")
        self.btn_files = QPushButton("Add files…")
        self.btn_scan = QPushButton("Scan")
        self.btn_fetch = QPushButton("Fetch missing")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_clear = QPushButton("Clear")
        self.mode = QComboBox()
        self.mode.addItems(["both", "sidecar", "embed"])
        self.mode.setCurrentText(cfg.output_mode)
        top.addWidget(self.btn_folder)
        top.addWidget(self.btn_files)
        top.addWidget(self.btn_scan)
        top.addWidget(self.btn_fetch)
        top.addWidget(self.btn_cancel)
        top.addWidget(self.btn_clear)
        top.addWidget(QLabel("Write:"))
        top.addWidget(self.mode)
        self.lbl_folder = QLabel("No folder selected — or drag & drop folders/files here")
        layout.addLayout(top)
        layout.addWidget(self.lbl_folder)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["File", "Title", "Artist", "Sidecar", "Embedded", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAcceptDrops(True)
        self.table.installEventFilter(self)
        layout.addWidget(self.table)
        self.lbl_prog = QLabel("")
        layout.addWidget(self.lbl_prog)

        self.btn_folder.clicked.connect(self.pick)
        self.btn_files.clicked.connect(self.pick_files)
        self.btn_scan.clicked.connect(self.scan)
        self.btn_fetch.clicked.connect(self.fetch)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_clear.clicked.connect(self.clear)
        self.mode.currentTextChanged.connect(self._mode_changed)

    # -- drag & drop -----------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.add_sources(paths)

    def eventFilter(self, obj: QObject, event: QEvent):
        # Table sits under the cursor for most drops — forward those to us.
        if obj is self.table:
            if event.type() == QEvent.DragEnter:
                self.dragEnterEvent(event)  # type: ignore[arg-type]
                return True
            if event.type() == QEvent.Drop:
                self.dropEvent(event)  # type: ignore[arg-type]
                return True
        return super().eventFilter(obj, event)

    # -- sources ----------------------------------------------------------
    def _mode_changed(self, t: str):
        self.cfg.output_mode = t
        self.cfg.save()

    def _refresh_label(self):
        if not self.sources:
            self.lbl_folder.setText("No folder selected — or drag & drop folders/files here")
        else:
            ndirs = sum(1 for s in self.sources if s.is_dir())
            nfiles = len(self.sources) - ndirs
            parts = []
            if ndirs:
                parts.append(f"{ndirs} folder(s)")
            if nfiles:
                parts.append(f"{nfiles} file(s)")
            names = ", ".join(s.name for s in self.sources[:3])
            extra = f" +{len(self.sources) - 3} more" if len(self.sources) > 3 else ""
            self.lbl_folder.setText(f"{' + '.join(parts)}: {names}{extra}")

    def add_sources(self, paths: list[Path]):
        added, skipped = 0, 0
        known = {s.resolve() for s in self.sources if s.exists()}
        for p in paths:
            if not p.exists():
                skipped += 1
                continue
            if p.is_dir() or (p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES):
                rp = p.resolve()
                if rp not in known:
                    known.add(rp)
                    self.sources.append(p)
                    added += 1
            else:
                skipped += 1
        self._refresh_label()
        if added:
            self.scan()
        msg = f"Added {added} source(s)"
        if skipped:
            msg += f", skipped {skipped} unsupported"
        msg += " (drop folders or audio files)."
        self.log.emit(msg)

    def pick(self):
        d = QFileDialog.getExistingDirectory(self, "Music library folder")
        if d:
            self.add_sources([Path(d)])

    def pick_files(self):
        exts = " ".join(f"*{s}" for s in sorted(SUPPORTED_SUFFIXES))
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add audio files", filter=f"Audio ({exts})")
        if files:
            self.add_sources([Path(f) for f in files])

    def scan(self):
        if not self.sources:
            self.log.emit("Pick a folder, add files, or drop them here first.")
            return
        self.records = scan_sources(self.sources, self.cfg)
        self.table.setRowCount(len(self.records))
        need = sum(1 for r in self.records if r.needs_fetch)
        for i, r in enumerate(self.records):
            vals = [r.audio_path.name, r.title, r.artist,
                    r.sidecar_kind if r.has_sidecar else "—",
                    r.embedded_kind,
                    "needs fetch" if r.needs_fetch else f"skip ({r.skip_reason})"]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(v))
        self.log.emit(f"Scanned {len(self.records)} tracks, {need} need lyrics.")

    def clear(self):
        """Remove all imported tracks (cancels any running batch first)."""
        if self.worker is not None:
            try:
                self.worker.runner.cancel()
            except Exception:
                pass
        self.worker = None
        self.sources = []
        self.records = []
        self.table.setRowCount(0)
        self.lbl_prog.setText("")
        self._refresh_label()
        self.log.emit("Cleared imported tracks.")

    def fetch(self):
        from PySide6.QtCore import QThread

        targets = [r for r in self.records if r.needs_fetch]
        if not targets:
            self.log.emit("Nothing to fetch.")
            return
        if "lrcred" in self.cfg.provider_order and not ensure_lrcred_contact(self, self.cfg):
            self.log.emit("lrc.red skipped: no contact email set.")
        self.thread = QThread(self)
        self.worker = Worker(targets, self.cfg)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(
            lambda d, t, name: self.lbl_prog.setText(f"{d}/{t} — {name}"))
        self.worker.progress.connect(
            lambda d, t, name: self.log.emit(f"[{d}/{t}] {name}"))
        self.worker.finished.connect(self._done)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def _done(self, outcomes: list):
        ok = sum(1 for o in outcomes if o.result is not None)
        self.log.emit(f"Batch done: {ok}/{len(outcomes)} found.")
        self.scan()

    def cancel(self):
        if self.worker:
            self.worker.runner.cancel()
            self.log.emit("Cancel requested.")
