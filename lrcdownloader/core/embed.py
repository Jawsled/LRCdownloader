"""Read / write embedded lyrics + kind classification.

Kind matters for skip logic (your requirement):
- MP3: SYLT frame = synced, USLT-only = plain
- FLAC/OGG/Opus (vorbis): LYRICS / UNSYNCEDLYRICS field content classified via lrc.classify_lrc
- M4A/MP4: ©lyr atom classified the same way
- WMA/WAV: best-effort via mutagen text fields
"""
from __future__ import annotations

from pathlib import Path

from lrcdownloader.core import lrc as lrc_utils


def read_embedded(path: Path) -> tuple[str, str]:
    """Return (kind, text). kind in none/plain/synced/enhanced."""
    try:
        return _read_embedded_inner(path)
    except Exception:
        return "none", ""


def _read_embedded_inner(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return _read_mp3(path)
    if suffix in (".flac", ".ogg", ".opus"):
        return _read_vorbis(path)
    if suffix in (".m4a", ".mp4"):
        return _read_mp4(path)
    return _read_generic(path)


def _read_mp3(path: Path) -> tuple[str, str]:
    from mutagen.id3 import ID3

    try:
        tags = ID3(str(path))
    except Exception:
        return "none", ""
    # SYLT = synced; check first
    try:
        for key in tags.keys():
            if key.startswith("SYLT"):
                frame = tags[key]
                txt = str(getattr(frame, "text", "") or "")
                if txt.strip():
                    return "synced", txt
    except Exception:
        pass
    try:
        for key in tags.keys():
            if key.startswith("USLT"):
                txt = str(tags[key].text or "").strip()
                if txt:
                    return lrc_utils.classify_lrc(txt), txt
    except Exception:
        pass
    return "none", ""


def _read_vorbis(path: Path) -> tuple[str, str]:
    from mutagen import File as MutagenFile

    f = MutagenFile(str(path))
    if f is None:
        return "none", ""
    for key in ("lyrics", "unsyncedlyrics", "LYRICS"):
        try:
            if key in f:
                v = f[key]
                txt = "\n".join(str(x) for x in (v if isinstance(v, list) else [v])).strip()
                if txt:
                    return lrc_utils.classify_lrc(txt), txt
        except Exception:
            continue
    return "none", ""


def _read_mp4(path: Path) -> tuple[str, str]:
    from mutagen.mp4 import MP4

    try:
        f = MP4(str(path))
    except Exception:
        return "none", ""
    try:
        v = f.tags.get("©lyr") if f.tags else None
        if v:
            txt = "\n".join(str(x) for x in v).strip()
            if txt:
                return lrc_utils.classify_lrc(txt), txt
    except Exception:
        pass
    return "none", ""


def _read_generic(path: Path) -> tuple[str, str]:
    from mutagen import File as MutagenFile

    try:
        f = MutagenFile(str(path), easy=True)
    except Exception:
        return "none", ""
    if f is None:
        return "none", ""
    for key in ("lyrics", "unsyncedlyrics"):
        try:
            v = f.get(key)
            if v:
                txt = "\n".join(str(x) for x in v).strip()
                if txt:
                    return lrc_utils.classify_lrc(txt), txt
        except Exception:
            continue
    return "none", ""


def write_embedded(path: Path, lrc_text: str) -> bool:
    """Write full LRC text (with tags) into the audio file. Returns success."""
    kind = lrc_utils.classify_lrc(lrc_text)
    suffix = path.suffix.lower()
    try:
        if suffix == ".mp3":
            return _write_mp3(path, lrc_text, kind)
        if suffix in (".flac", ".ogg", ".opus"):
            return _write_vorbis(path, lrc_text)
        if suffix in (".m4a", ".mp4"):
            return _write_mp4(path, lrc_text)
        return _write_generic(path, lrc_text)
    except Exception:
        return False


def _write_mp3(path: Path, text: str, kind: str) -> bool:
    from mutagen.id3 import ID3, USLT

    try:
        try:
            tags = ID3(str(path))
        except Exception:
            tags = ID3()
        # Replace/add USLT (players read this); drop stale SYLT only if we write plain?
        # Keep SYLT removal minimal: leave existing SYLT when writing synced text.
        tags.delall("USLT")
        tags.add(USLT(encoding=3, lang="eng", desc="", text=text))
        tags.save(str(path))
        return True
    except Exception:
        return False


def _write_vorbis(path: Path, text: str) -> bool:
    from mutagen import File as MutagenFile

    f = MutagenFile(str(path))
    if f is None:
        return False
    f["lyrics"] = text
    f.save()
    return True


def _write_mp4(path: Path, text: str) -> bool:
    from mutagen.mp4 import MP4

    f = MP4(str(path))
    if f.tags is None:
        f.add_tags()
    f.tags["©lyr"] = [text]
    f.save()
    return True


def _write_generic(path: Path, text: str) -> bool:
    from mutagen import File as MutagenFile

    f = MutagenFile(str(path), easy=True)
    if f is None:
        return False
    try:
        f["lyrics"] = [text]
        f.save()
        return True
    except Exception:
        return False
