"""lrc.red client (free, no API key; identify your app + credit lrc.red).

Docs: https://lrc.red/api
- GET /search.json?q=          -> {"hits": [...], "next": "..."}
- GET /s/{isrc}.json           -> track metadata ("sync": "none" | "line" | "word")
- GET /s/{isrc}.lrc            -> enhanced LRC, only for timed tracks

Terms require a User-Agent naming the app with a link and contact email, and
credit/link back to lrc.red wherever lyrics are shown. Untimed catalog entries
return obfuscated text, so this provider only accepts line/word-synced tracks.
"""
from __future__ import annotations

import httpx

from lrcdownloader import __version__
from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.providers.base import LrcResult, LyricsProvider
from lrcdownloader.core.providers.select import pick_candidate, rank_by_match, split_query

BASE = "https://lrc.red"
REPO = "https://github.com/Jawsled/LRCdownloader"
PAGE_SIZE = 30


def user_agent(contact: str = "") -> str:
    ua = f"LRCdownloader/{__version__} (+{REPO})"
    if contact:
        ua += f" mailto:{contact}"
    return ua


class LrcRedProvider(LyricsProvider):
    name = "lrcred"

    def __init__(self, timeout_s: float = 12.0, contact: str = "",
                 client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self.contact = contact
        self._client = client

    def _client_or(self) -> tuple[httpx.Client, bool]:
        if self._client is not None:
            return self._client, False
        headers = {
            "User-Agent": user_agent(self.contact),
            "Accept": "application/json",
        }
        return httpx.Client(timeout=self.timeout_s, headers=headers,
                            follow_redirects=True), True

    def _search_hits(self, query: str) -> list[dict]:
        client, close = self._client_or()
        try:
            r = client.get(f"{BASE}/search.json", params={"q": query})
            r.raise_for_status()
            data = r.json()
            return list(data.get("hits") or [])[:PAGE_SIZE]
        finally:
            if close:
                client.close()

    def _fetch_isrc(self, isrc: str, match: float = 0.7) -> LrcResult | None:
        client, close = self._client_or()
        try:
            meta_r = client.get(f"{BASE}/s/{isrc}.json")
            if meta_r.status_code == 404:
                return None
            meta_r.raise_for_status()
            meta = meta_r.json()
            sync = str(meta.get("sync") or "none").lower()
            if sync not in ("line", "word"):
                return None
            lrc_r = client.get(f"{BASE}/s/{isrc}.lrc")
            if lrc_r.status_code == 404:
                return None
            lrc_r.raise_for_status()
            text = lrc_r.text.strip()
        except (httpx.HTTPError, ValueError, KeyError, AttributeError):
            return None
        finally:
            if close:
                client.close()
        kind = lrc_utils.classify_lrc(text)
        if kind not in ("synced", "enhanced"):
            return None
        base = 0.92 if sync == "word" or kind == "enhanced" else 0.88
        return LrcResult(lrc_text=text, kind=kind, source="lrc.red",
                         score=base * max(match, 0.5))

    def search(self, title: str, artist: str, album: str = "",
               duration_s: float = 0.0) -> LrcResult | None:
        if not title or not self.contact.strip():
            # lrc.red's terms require identifying the client with a contact.
            return None
        query = " ".join(x for x in (artist, title) if x).strip()
        try:
            hits = self._search_hits(query)
        except (httpx.HTTPError, ValueError, AttributeError):
            return None
        hit, match = pick_candidate(
            hits, title, artist, duration_s,
            get_title=lambda h: str(h.get("title") or ""),
            get_artist=lambda h: str(h.get("artist") or ""),
            get_duration=lambda h: float(h.get("duration") or 0.0),
        )
        if hit is None:
            return None
        isrc = str(hit.get("isrc") or "")
        if not isrc:
            return None
        return self._fetch_isrc(isrc, match)

    def search_text(self, query: str) -> list[LrcResult]:
        if not self.contact.strip():
            return []
        try:
            hits = self._search_hits(query)
        except (httpx.HTTPError, ValueError, AttributeError):
            return []
        title, artist = split_query(query)
        hits = rank_by_match(
            hits, title, artist,
            get_title=lambda h: str(h.get("title") or ""),
            get_artist=lambda h: str(h.get("artist") or ""),
            get_duration=lambda h: float(h.get("duration") or 0.0),
        )
        out: list[LrcResult] = []
        for hit in hits[:6]:
            res = self._fetch_isrc(str(hit.get("isrc") or ""), 0.7)
            if res is not None:
                out.append(res)
        return out
