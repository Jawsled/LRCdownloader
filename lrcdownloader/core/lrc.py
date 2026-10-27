"""LRC parse / classify / build helpers.

Kinds: 'none' | 'plain' | 'synced' | 'enhanced'
- plain: lines without timestamps
- synced: [mm:ss.xx] line tags
- enhanced: word-level karaoke <mm:ss.xx> tags
"""
from __future__ import annotations

import re

LINE_TAG = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")
WORD_TAG = re.compile(r"<\d{1,3}:\d{2}(?:[.:]\d{1,3})?>")
ZERO_TAG = re.compile(r"\[00:00\.?0*0?\]")

NONZERO_LINE = re.compile(r"\[(?!00:00\.00\])(?:\d{1,3}:\d{2}[.:]\d+)\]")


def classify_lrc(text: str) -> str:
    if not text or not text.strip():
        return "none"
    t = text.strip()
    if WORD_TAG.search(t):
        return "enhanced"
    tags = LINE_TAG.findall(t)
    if not tags:
        return "plain"
    # synced only if at least one non-zero timestamp exists
    if NONZERO_LINE.search(t):
        return "synced"
    return "plain"


def is_synced(text: str) -> bool:
    return classify_lrc(text) in ("synced", "enhanced")


def strip_tags(text: str) -> str:
    out = []
    for line in text.splitlines():
        line = LINE_TAG.sub("", line)
        line = WORD_TAG.sub("", line).strip()
        if line:
            out.append(line)
    return "\n".join(out)


_INSTRUMENTAL_MARKERS = (
    "纯音乐", "没有填词", "此歌曲为没有填词的纯音乐", "无歌词",
    "版权原因", "instrumental", "no lyrics",
)


def looks_instrumental(text: str) -> bool:
    """Detect placeholder lyrics for instrumental tracks (short text only)."""
    plain = strip_tags(text)
    if not plain or len(plain) > 200:
        return False
    low = plain.lower()
    return any(marker in low for marker in _INSTRUMENTAL_MARKERS)


def validate_lrc(text: str, *, require_synced: bool = False) -> tuple[bool, str]:
    kind = classify_lrc(text)
    if kind == "none":
        return False, "empty lyrics"
    if require_synced and kind not in ("synced", "enhanced"):
        return False, "no synced timestamps"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 1:
        return False, "no lyric lines"
    return True, f"ok ({kind}, {len(lines)} lines)"


def ms_to_tag(ms: int) -> str:
    ms = max(0, int(ms))
    m = ms // 60000
    s = (ms % 60000) // 1000
    cs = ((ms % 1000) // 10)
    return f"{m:02d}:{s:02d}.{cs:02d}"


def build_lrc(lines: list[tuple[int, str]]) -> str:
    """Build LRC from (start_ms, text) pairs."""
    out = ["[ti:]", "[ar:]", "[al:]", "[by:LRCdownloader]"]
    for ms, words in lines:
        out.append(f"[{ms_to_tag(ms)}]{words}")
    return "\n".join(out) + "\n"


def build_plain(lines: list[tuple[int, str]]) -> str:
    return "\n".join(w for _, w in lines if w.strip()) + "\n"
