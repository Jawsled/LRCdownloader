"""Batch engine: concurrent fetch + write with cancel/pause + retry-failed."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from lrcdownloader.config import Settings
from lrcdownloader.core import embed as embed_utils
from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.providers.base import LrcResult
from lrcdownloader.core.providers.lrclib import LrclibProvider
from lrcdownloader.core.providers.matcher import fetch_first
from lrcdownloader.core.providers.spotify_api import SpotifyLyricsProvider
from lrcdownloader.core.providers.syncedlyrics_adapter import SyncedLyricsProvider
from lrcdownloader.core.scanner import SongRecord
from lrcdownloader.credentials import get_secret


@dataclass
class FetchOutcome:
    record: SongRecord
    result: LrcResult | None
    wrote_sidecar: bool
    wrote_embed: bool
    message: str


ProgressCb = Callable[[int, int, str], None]  # done, total, label


def build_providers(cfg: Settings):
    from lrcdownloader.core.providers.base import LyricsProvider

    providers: list[LyricsProvider] = []
    order = cfg.provider_order
    if "lrclib" in order:
        providers.append(LrclibProvider(timeout_s=cfg.timeout_s))
    if "syncedlyrics" in order:
        providers.append(SyncedLyricsProvider(providers=cfg.syncedlyrics_providers))
    if "spotify" in order:
        providers.append(SpotifyLyricsProvider(
            api_base=cfg.spotify_api_base,
            sp_dc=get_secret("SP_DC"),
            timeout_s=cfg.timeout_s,
            client_id=get_secret("SPOTIFY_CLIENT_ID"),
            client_secret=get_secret("SPOTIFY_CLIENT_SECRET"),
        ))
    # keep configured order
    rank = {n: i for i, n in enumerate(order)}
    providers.sort(key=lambda p: rank.get(p.name, 99))
    return providers


def write_outputs(record: SongRecord, res: LrcResult, cfg: Settings) -> tuple[bool, bool]:
    wrote_sc, wrote_em = False, False
    if cfg.output_mode in ("sidecar", "both"):
        exists = record.sidecar_path.exists()
        if not exists or cfg.overwrite == "force" or (
            exists and cfg.overwrite == "missing" and record.sidecar_kind == "none"
        ):
            record.sidecar_path.write_text(res.lrc_text, encoding="utf-8")
            wrote_sc = True
    if cfg.output_mode in ("embed", "both"):
        should = (
            cfg.overwrite == "force"
            or record.embedded_kind == "none"
            or (record.embedded_kind == "plain" and res.synced)
        )
        if should:
            wrote_em = bool(embed_utils.write_embedded(record.audio_path, res.lrc_text))
    return wrote_sc, wrote_em


class BatchRunner:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._pause.set()

    def cancel(self) -> None:
        self._cancel.set()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._pause.clear()
        else:
            self._pause.set()

    def run(self, records: list[SongRecord],
            on_progress: ProgressCb | None = None) -> list[FetchOutcome]:
        targets = [r for r in records if r.needs_fetch]
        total = len(targets)
        outcomes: list[FetchOutcome] = []
        if not targets:
            return outcomes
        providers = build_providers(self.cfg)

        def one(rec: SongRecord) -> FetchOutcome:
            self._pause.wait()
            if self._cancel.is_set():
                return FetchOutcome(rec, None, False, False, "cancelled")
            try:
                res = fetch_first(providers, rec.title, rec.artist, rec.album,
                                  rec.duration_s, self.cfg)
            except Exception as e:  # noqa: BLE001
                return FetchOutcome(rec, None, False, False, f"error: {e}")
            if res is None:
                return FetchOutcome(rec, None, False, False, "not found")
            ok, msg = lrc_utils.validate_lrc(res.lrc_text,
                                             require_synced=self.cfg.synced_only)
            if not ok:
                return FetchOutcome(rec, res, False, False, msg)
            try:
                ws, we = write_outputs(rec, res, self.cfg)
            except Exception as e:  # noqa: BLE001
                return FetchOutcome(rec, res, False, False, f"write failed: {e}")
            return FetchOutcome(rec, res, ws, we,
                                f"{res.source} ({res.kind})")

        done = 0
        with ThreadPoolExecutor(max_workers=max(1, self.cfg.concurrency)) as ex:
            futs = {ex.submit(one, r): r for r in targets}
            for fut in as_completed(futs):
                if self._cancel.is_set():
                    for f in futs:
                        f.cancel()
                    break
                oc = fut.result()
                outcomes.append(oc)
                done += 1
                if on_progress:
                    on_progress(done, total, oc.record.audio_path.name)
        return outcomes
