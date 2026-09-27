"""syncedlyrics adapter (multi-provider fallback).

Upstream: https://github.com/moehmeni/syncedlyrics
Providers used: NetEase, Musixmatch, Megalobiz, Lrclib (+Genius plain-only).
Deezer/Lyricsify excluded (broken upstream).
"""
from __future__ import annotations

from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.providers.base import LrcResult, LyricsProvider


class SyncedLyricsProvider(LyricsProvider):
    name = "syncedlyrics"

    def __init__(self, providers: list[str] | None = None, timeout_s: float = 20.0):
        self.providers = providers or ["NetEase", "Musixmatch", "Megalobiz", "Lrclib"]
        self.timeout_s = timeout_s

    def search(self, title: str, artist: str, album: str = "",
               duration_s: float = 0.0) -> LrcResult | None:
        try:
            import syncedlyrics
        except ImportError:
            return None
        term = f"{title} {artist}".strip()
        for prov in self.providers:
            try:
                text = syncedlyrics.search(term, providers=[prov])
            except Exception:
                continue
            if not text:
                continue
            kind = lrc_utils.classify_lrc(text)
            return LrcResult(lrc_text=text, kind=kind,
                             source=f"syncedlyrics:{prov}", score=0.6)
        return None
