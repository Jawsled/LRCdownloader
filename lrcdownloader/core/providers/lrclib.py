"""LRCLIB client (default source, no auth).

Docs: https://lrclib.net/docs
- GET /api/get?artist_name=&track_name=&album_name=&duration=  (exact, duration-aware)
- GET /api/search?q=  (manual search candidates)
- GET /api/get-cached?artist_name=&track_name=&album_name=&duration=
Requires a descriptive User-Agent per publisher rules.
"""
from __future__ import annotations

import httpx

from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.providers.base import LrcResult, LyricsProvider

BASE = "https://lrclib.net"
UA = {"User-Agent": "LRCdownloader/0.1.0 (desktop SongSync port)"}


class LrclibProvider(LyricsProvider):
    name = "lrclib"

    def __init__(self, timeout_s: float = 12.0, client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self._client = client

    def _client_or(self) -> httpx.Client:
        return self._client or httpx.Client(timeout=self.timeout_s, headers=UA)

    def search(self, title: str, artist: str, album: str = "",
               duration_s: float = 0.0) -> LrcResult | None:
        params: dict[str, str] = {"track_name": title, "artist_name": artist}
        if album:
            params["album_name"] = album
        if duration_s and duration_s > 0:
            params["duration"] = str(round(duration_s, 1))
        close = False
        client = self._client_or()
        try:
            r = client.get(f"{BASE}/api/get", params=params)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
        finally:
            if self._client is None:
                client.close()
        synced = (data.get("syncedLyrics") or "").strip()
        plain = (data.get("plainLyrics") or "").strip()
        text = synced or plain
        if not text:
            return None
        kind = lrc_utils.classify_lrc(text)
        return LrcResult(lrc_text=text, kind=kind, source="lrclib",
                         score=1.0 if synced else 0.7, plain_text=plain)

    def search_text(self, query: str) -> list[LrcResult]:
        import httpx as _hx

        with _hx.Client(timeout=self.timeout_s, headers=UA) as c:
            r = c.get(f"{BASE}/api/search", params={"q": query})
            r.raise_for_status()
            items = r.json() or []
        out: list[LrcResult] = []
        for it in items[:10]:
            text = (it.get("syncedLyrics") or it.get("plainLyrics") or "").strip()
            if not text:
                continue
            out.append(LrcResult(
                lrc_text=text,
                kind=lrc_utils.classify_lrc(text),
                source="lrclib",
                score=float(it.get("duration") and 0.8 or 0.6),
                plain_text=(it.get("plainLyrics") or ""),
            ))
        return out
