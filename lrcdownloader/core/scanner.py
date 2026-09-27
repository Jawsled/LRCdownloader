"""Library scanner: filesystem walk + scan-first skip logic.

Sidecar naming: same dir + same audio basename, extension swapped to .lrc.
Embed skip is kind-aware (see core/embed.py + Settings.embed_skip_mode).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lrcdownloader.config import Settings
from lrcdownloader.core import embed as embed_utils
from lrcdownloader.core import lrc as lrc_utils
from lrcdownloader.core.metadata import SUPPORTED_SUFFIXES, read_metadata


@dataclass
class SongRecord:
    audio_path: Path
    sidecar_path: Path
    title: str
    artist: str
    album: str
    duration_s: float
    has_sidecar: bool
    sidecar_kind: str  # none/plain/synced/enhanced
    embedded_kind: str
    needs_fetch: bool
    skip_reason: str = ""


def sidecar_for(audio: Path) -> Path:
    return audio.with_suffix(".lrc")


def _classify_sidecar(p: Path) -> str:
    if not p.exists():
        return "none"
    try:
        return lrc_utils.classify_lrc(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return "none"


def should_skip(has_sidecar_kind: str, embedded_kind: str, cfg: Settings) -> tuple[bool, str]:
    if cfg.skip_if_sidecar and has_sidecar_kind != "none":
        return True, f"sidecar exists ({has_sidecar_kind})"
    mode = cfg.embed_skip_mode
    if mode == "none":
        return False, ""
    if mode == "any" and embedded_kind != "none":
        return True, f"embedded exists ({embedded_kind})"
    if mode == "synced_or_better" and embedded_kind in ("synced", "enhanced"):
        return True, f"embedded synced ({embedded_kind})"
    return False, ""


def _record_for(audio: Path, cfg: Settings) -> SongRecord:
    meta = read_metadata(audio)
    sc = sidecar_for(audio)
    sc_kind = _classify_sidecar(sc)
    emb_kind, _ = embed_utils.read_embedded(audio)
    skip, reason = should_skip(sc_kind if sc.exists() else "none", emb_kind, cfg)
    if cfg.overwrite == "force":
        skip, reason = False, ""
    return SongRecord(
        audio_path=audio,
        sidecar_path=sc,
        title=meta.title,
        artist=meta.artist,
        album=meta.album,
        duration_s=meta.duration_s,
        has_sidecar=sc.exists(),
        sidecar_kind=sc_kind if sc.exists() else "none",
        embedded_kind=emb_kind,
        needs_fetch=not skip,
        skip_reason=reason,
    )


def scan_library(root: Path, cfg: Settings) -> list[SongRecord]:
    files = sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    return [_record_for(audio, cfg) for audio in files]


def scan_sources(sources: list[Path], cfg: Settings) -> list[SongRecord]:
    """Scan a mix of dropped/picked folders and individual audio files.

    Folders are walked recursively; audio files are taken directly.
    Results are deduplicated by resolved audio path and sorted.
    """
    seen: set[Path] = set()
    files: list[Path] = []
    for src in sources:
        try:
            p = Path(src)
        except Exception:
            continue
        if not p.exists():
            continue
        if p.is_dir():
            for f in sorted(
                x for x in p.rglob("*")
                if x.is_file() and x.suffix.lower() in SUPPORTED_SUFFIXES
            ):
                rp = f.resolve()
                if rp not in seen:
                    seen.add(rp)
                    files.append(f)
        elif p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES:
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                files.append(p)
    files.sort(key=lambda x: str(x).lower())
    return [_record_for(audio, cfg) for audio in files]
