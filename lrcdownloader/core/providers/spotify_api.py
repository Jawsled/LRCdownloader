"""Spotify Lyrics API client (opt-in; needs self-hosted instance + SP_DC).

Upstream: https://github.com/akashrchandran/spotify-lyrics-api
- Deploy (docker/composer) with SP_DC cookie, then GET /?trackid=...&format=lrc
- Track-ID resolution: Spotify Web API search (client-credentials) or pasted track URL.
- WARNING: likely against Spotify TOS — disabled by default, explicit opt-in only.
"""
from __future__ import annotations

import base64
import re

import httpx

from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.providers.base import LrcResult, LyricsProvider

_TRACK_RE = re.compile(r"(?:open\.spotify\.com/track/|spotify:track:)([A-Za-z0-9]{10,})")


def extract_track_id(url_or_id: str) -> str:
    s = url_or_id.strip()
    m = _TRACK_RE.search(s)
    return m.group(1) if m else s


class SpotifyLyricsProvider(LyricsProvider):
    name = "spotify"

    def __init__(self, api_base: str = "http://localhost:8080",
                 sp_dc: str = "", timeout_s: float = 12.0,
                 client_id: str = "", client_secret: str = ""):
        self.api_base = api_base.rstrip("/")
        self.sp_dc = sp_dc
        self.timeout_s = timeout_s
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    def configured(self) -> bool:
        return bool(self.api_base)

    def resolve_track_id(self, title: str, artist: str) -> str | None:
        if not (self.client_id and self.client_secret):
            return None
        creds = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        with httpx.Client(timeout=self.timeout_s) as c:
            tok = c.post("https://accounts.spotify.com/api/token",
                         headers={"Authorization": f"Basic {creds}"},
                         data={"grant_type": "client_credentials"}).json()
            token = tok.get("access_token")
            if not token:
                return None
            q = f"track:{title} artist:{artist}"
            r = c.get("https://api.spotify.com/v1/search",
                      headers={"Authorization": f"Bearer {token}"},
                      params={"q": q, "type": "track", "limit": 1}).json()
            try:
                return r["tracks"]["items"][0]["id"]
            except Exception:
                return None

    def fetch_by_track_id(self, track_id: str) -> LrcResult | None:
        with httpx.Client(timeout=self.timeout_s) as c:
            r = c.get(f"{self.api_base}/", params={"trackid": track_id, "format": "lrc"})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
        if data.get("error"):
            return None
        lines = data.get("lines") or []
        pairs: list[tuple[int, str]] = []
        for ln in lines:
            tag = str(ln.get("timeTag", "00:00.00"))
            words = str(ln.get("words", ""))
            pairs.append((_tag_to_ms(tag), words))
        text = lrc_utils.build_lrc(pairs)
        kind = lrc_utils.classify_lrc(text)
        return LrcResult(lrc_text=text, kind=kind, source="spotify", score=0.55)

    def search(self, title: str, artist: str, album: str = "",
               duration_s: float = 0.0) -> LrcResult | None:
        tid = self.resolve_track_id(title, artist)
        if not tid:
            return None
        try:
            return self.fetch_by_track_id(tid)
        except Exception:
            return None


def _tag_to_ms(tag: str) -> int:
    m = re.match(r"(\d+):(\d+)(?:[.:](\d+))?", tag.strip())
    if not m:
        return 0
    mm, ss, frac = int(m.group(1)), int(m.group(2)), m.group(3) or "0"
    ms = mm * 60000 + ss * 1000
    if len(frac) == 2:
        ms += int(frac) * 10
    elif len(frac) == 3:
        ms += int(frac)
    elif len(frac) == 1:
        ms += int(frac) * 100
    return ms
