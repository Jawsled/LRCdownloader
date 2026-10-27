"""NetEase Cloud Music lyrics (unofficial web API, no key).

- Search: https://music.163.com/api/search/get?s=&type=1&limit=
- Lyrics: https://music.163.com/api/song/lyric?id=&lv=1&kv=1&tv=-1&os=pc

This is an unofficial endpoint and can be rate-limited or changed without
notice. It is especially useful for Chinese/CJK catalog coverage. NetEase also
returns `tlyric` (translations) and `klyric` (karaoke); we currently keep the
original lyric only so the output stays a standard LRC file.
"""
from __future__ import annotations

import httpx

from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.providers.base import LrcResult, LyricsProvider
from lrcdownloader.core.providers.select import pick_candidate, rank_by_match, split_query

SEARCH = "https://music.163.com/api/search/get"
LYRIC = "https://music.163.com/api/song/lyric"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Referer": "https://music.163.com/",
    "Accept": "application/json",
}


def _song_title(song: dict) -> str:
    return str(song.get("name") or "")


def _song_artist(song: dict) -> str:
    artists = song.get("artists") or song.get("ar") or []
    return ", ".join(str(a.get("name") or "") for a in artists if a.get("name"))


def _song_duration(song: dict) -> float:
    try:
        ms = song.get("duration") or song.get("dt") or 0
        return float(ms) / 1000.0
    except (TypeError, ValueError):
        return 0.0


class NeteaseProvider(LyricsProvider):
    name = "netease"

    def __init__(self, timeout_s: float = 12.0,
                 client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self._client = client

    def _client_or(self) -> tuple[httpx.Client, bool]:
        if self._client is not None:
            return self._client, False
        return httpx.Client(timeout=self.timeout_s, headers=HEADERS,
                            follow_redirects=True), True

    def _search_songs(self, query: str, limit: int = 100) -> list[dict]:
        client, close = self._client_or()
        try:
            r = client.get(SEARCH, params={
                "s": query, "type": 1, "limit": limit, "offset": 0,
            })
            r.raise_for_status()
            data = r.json()
            return list((data.get("result") or {}).get("songs") or [])
        finally:
            if close:
                client.close()

    def _fetch_song(self, song: dict, match: float = 0.7) -> LrcResult | None:
        song_id = song.get("id")
        if not song_id:
            return None
        client, close = self._client_or()
        try:
            r = client.get(LYRIC, params={
                "id": song_id, "lv": 1, "kv": 1, "tv": -1, "os": "pc",
            })
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError, AttributeError):
            return None
        finally:
            if close:
                client.close()
        if data.get("nolyric") or data.get("uncollected"):
            return None
        text = str((data.get("lrc") or {}).get("lyric") or "").strip()
        if not text or lrc_utils.looks_instrumental(text):
            return None
        kind = lrc_utils.classify_lrc(text)
        if kind == "none":
            return None
        score = (0.86 if kind in ("synced", "enhanced") else 0.55) * max(match, 0.5)
        return LrcResult(lrc_text=text, kind=kind, source="netease",
                         score=score,
                         plain_text="" if kind in ("synced", "enhanced") else text)

    def search(self, title: str, artist: str, album: str = "",
               duration_s: float = 0.0) -> LrcResult | None:
        if not title:
            return None
        query = " ".join(x for x in (title, artist) if x).strip()
        try:
            songs = self._search_songs(query)
        except (httpx.HTTPError, ValueError, AttributeError):
            return None
        song, match = pick_candidate(
            songs, title, artist, duration_s,
            get_title=_song_title,
            get_artist=_song_artist,
            get_duration=_song_duration,
        )
        if song is None:
            return None
        return self._fetch_song(song, match)

    def search_text(self, query: str) -> list[LrcResult]:
        try:
            songs = self._search_songs(query)
        except (httpx.HTTPError, ValueError, AttributeError):
            return []
        title, artist = split_query(query)
        songs = rank_by_match(
            songs, title, artist,
            get_title=_song_title,
            get_artist=_song_artist,
            get_duration=_song_duration,
        )
        out: list[LrcResult] = []
        for song in songs[:6]:
            res = self._fetch_song(song, 0.7)
            if res is not None:
                out.append(res)
        return out
