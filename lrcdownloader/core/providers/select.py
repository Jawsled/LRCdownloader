"""Shared candidate matching for search-based providers.

Used by lrc.red / NetEase / QQ providers: fuzzy title+artist similarity with a
duration bonus/penalty. Title similarity blends plain ratio with token-set
ratio so short CJK titles still match variants like "晴天 (Live)" while an
exact title gets the top score.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable, TypeVar

from rapidfuzz import fuzz

T = TypeVar("T")

_NON_WORD = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)


def _norm(text: str) -> str:
    return " ".join(_NON_WORD.sub(" ", (text or "").lower()).split())


def _title_score(cand_title: str, title: str) -> float:
    nct, nt = _norm(cand_title), _norm(title)
    if not nt or not nct:
        return 0.0
    if nct == nt:
        return 1.0
    ratio = fuzz.ratio(nct, nt) / 100.0
    token = fuzz.token_set_ratio(nct, nt) / 100.0 * 0.9
    return max(ratio, token)


def match_score(title: str, artist: str, duration_s: float,
                cand_title: str, cand_artist: str, cand_duration_s: float,
                tolerance_s: float = 10.0) -> float:
    """Score one candidate in the 0..1 range (higher is better)."""
    title_s = _title_score(cand_title, title)
    if not title_s:
        return 0.0
    if artist and cand_artist:
        artist_s = fuzz.token_set_ratio(_norm(cand_artist), _norm(artist)) / 100.0
    else:
        artist_s = 0.5
    score = 0.6 * title_s + 0.4 * artist_s
    if artist and cand_artist and artist_s < 0.35:
        score *= 0.65
    if duration_s and cand_duration_s:
        diff = abs(float(duration_s) - float(cand_duration_s))
        if diff <= tolerance_s:
            score += 0.15 * (1.0 - diff / max(tolerance_s, 1.0))
        else:
            score *= max(0.4, 1.0 - (diff - tolerance_s) / 120.0)
    if _norm(cand_title) == _norm(title):
        score += 0.05
    return min(1.0, score)


def pick_candidate(candidates: Iterable[T], title: str, artist: str,
                   duration_s: float,
                   get_title: Callable[[T], str],
                   get_artist: Callable[[T], str],
                   get_duration: Callable[[T], float],
                   min_title: float = 0.5) -> tuple[T | None, float]:
    """Return the best candidate and its match score."""
    best: T | None = None
    best_key = (-1.0, False, False)
    nt = _norm(title)
    na = _norm(artist)
    for cand in candidates:
        cand_title = get_title(cand)
        if _title_score(cand_title, title) < min_title:
            continue
        cand_artist = get_artist(cand)
        score = match_score(title, artist, duration_s, cand_title,
                            cand_artist, get_duration(cand))
        key = (score,
               _norm(cand_title) == nt,
               bool(na) and _norm(cand_artist) == na)
        if key > best_key:
            best, best_key = cand, key
    return best, best_key[0]


def split_query(query: str) -> tuple[str, str]:
    """Split a manual-search query into (title, artist)."""
    if " - " in query:
        artist, title = query.split(" - ", 1)
        return title.strip(), artist.strip()
    return query.strip(), ""


def rank_by_match(candidates: Iterable[T], title: str, artist: str,
                  get_title: Callable[[T], str],
                  get_artist: Callable[[T], str],
                  get_duration: Callable[[T], float]) -> list[T]:
    """Sort manual-search hits by title/artist similarity (best first)."""
    return sorted(
        candidates,
        key=lambda c: match_score(title, artist, 0.0, get_title(c),
                                  get_artist(c), get_duration(c)),
        reverse=True,
    )
