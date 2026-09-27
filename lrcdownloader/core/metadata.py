"""Audio metadata: mutagen tags first, filename fallback (SongSync-style)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SUFFIXES = {".mp3", ".flac", ".m4a", ".mp4", ".ogg", ".opus", ".wma", ".wav"}

_FILENAME_PATTERNS = [
    re.compile(r"^(?P<artist>.+?)\s*-\s*(?P<title>.+?)$"),  # Artist - Title
]


@dataclass
class TrackMeta:
    title: str
    artist: str
    album: str = ""
    duration_s: float = 0.0


def parse_filename(stem: str) -> tuple[str, str]:
    s = stem.strip()
    # strip leading track numbers like "01 - ", "01. "
    s = re.sub(r"^\d{1,3}\s*[.\-_ ]\s*", "", s)
    for pat in _FILENAME_PATTERNS:
        m = pat.match(s)
        if m:
            return m.group("title").strip(), m.group("artist").strip()
    return s, ""


def read_metadata(path: Path) -> TrackMeta:
    title, artist = parse_filename(path.stem)
    album, duration = "", 0.0
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(str(path), easy=True)
        if audio is not None:
            def first(key: str) -> str:
                try:
                    v = audio.get(key)
                    if isinstance(v, list) and v:
                        return str(v[0]).strip()
                except Exception:
                    pass
                return ""

            t = first("title") or first("©nam")
            a = first("artist") or first("©ART")
            al = first("album") or first("©alb")
            if t:
                title = t
            if a:
                artist = a
            if al:
                album = al
            try:
                if getattr(audio, "info", None) and getattr(audio.info, "length", None):
                    duration = float(audio.info.length)
            except Exception:
                pass
    except Exception:
        pass
    return TrackMeta(title=title, artist=artist, album=album, duration_s=duration)
