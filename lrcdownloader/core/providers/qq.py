"""QQ Music lyrics (unofficial web API, no key).

- Search: https://c.y.qq.com/soso/fcgi-bin/client_search_cp?w=&format=json&n=
- Lyrics: https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid=
          &format=json&nobase64=1

Unofficial endpoints; the Referer header is required. QQ occasionally returns
base64 even with nobase64=1, so decoding is handled defensively. QRC word-level
timing is not used here; the standard LRC field is enough for this app.
"""
from __future__ import annotations

import base64
import html

import httpx

from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.providers.base import LrcResult, LyricsProvider
from lrcdownloader.core.providers.select import pick_candidate, rank_by_match, split_query

SEARCH = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
LYRIC = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Referer": "https://y.qq.com/",
    "Origin": "https://y.qq.com",
    "Accept": "application/json",
}


def _song_title(song: dict) -> str:
    return str(song.get("songname") or song.get("title") or "")


def _song_artist(song: dict) -> str:
    singers = song.get("singer") or []
    if isinstance(singers, list):
        return ", ".join(str(s.get("name") or "") for s in singers if s.get("name"))
    return ""


def _song_duration(song: dict) -> float:
    try:
        return float(song.get("interval") or 0)
    except (TypeError, ValueError):
        return 0.0


def _decode_lyric(raw: str) -> str:
    text = html.unescape((raw or "").strip())
    if text and not text.lstrip().startswith("["):
        try:
            decoded = base64.b64decode(text, validate=True).decode("utf-8")
            if "[" in decoded:
                return decoded.strip()
        except (ValueError, UnicodeDecodeError):
            pass
    return text


class QQProvider(LyricsProvider):
    name = "qq"

    def __init__(self, timeout_s: float = 12.0,
                 client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self._client = client

    def _client_or(self) -> tuple[httpx.Client, bool]:
        if self._client is not None:
            return self._client, False
        return httpx.Client(timeout=self.timeout_s, headers=HEADERS,
                            follow_redirects=True), True

    def _search_songs(self, query: str, limit: int = 30) -> list[dict]:
        client, close = self._client_or()
        try:
            r = client.get(SEARCH, params={
                "w": query, "format": "json", "n": limit, "p": 1,
            })
            r.raise_for_status()
            data = r.json()
            return list((((data.get("data") or {}).get("song") or {})
                         .get("list")) or [])
        finally:
            if close:
                client.close()

    def _fetch_song(self, song: dict, match: float = 0.7) -> LrcResult | None:
        song_mid = song.get("songmid") or song.get("mid")
        if not song_mid:
            return None
        client, close = self._client_or()
        try:
            r = client.get(LYRIC, params={
                "songmid": song_mid, "format": "json", "nobase64": 1,
            })
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError, AttributeError):
            return None
        finally:
            if close:
                client.close()
        if data.get("retcode") not in (0, None) or data.get("code") not in (0, None):
            return None
        text = _decode_lyric(str(data.get("lyric") or ""))
        if not text or lrc_utils.looks_instrumental(text):
            return None
        kind = lrc_utils.classify_lrc(text)
        if kind == "none":
            return None
        score = (0.84 if kind in ("synced", "enhanced") else 0.55) * max(match, 0.5)
        return LrcResult(lrc_text=text, kind=kind, source="qq",
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
