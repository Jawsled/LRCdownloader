"""Provider interface + shared result type."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LrcResult:
    lrc_text: str
    kind: str  # plain/synced/enhanced
    source: str  # 'lrclib' | 'syncedlyrics:NetEase' | 'spotify'
    score: float = 0.0  # 0..1 match quality
    plain_text: str = ""

    @property
    def synced(self) -> bool:
        return self.kind in ("synced", "enhanced")


class LyricsProvider:
    name = "base"

    def search(self, title: str, artist: str, album: str = "",
               duration_s: float = 0.0) -> LrcResult | None:
        raise NotImplementedError

    def search_text(self, query: str) -> list[LrcResult]:
        """Manual-search candidates (may return multiple). Default: single search."""
        return []
