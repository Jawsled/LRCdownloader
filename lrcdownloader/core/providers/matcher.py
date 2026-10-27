"""Fallback orchestrator: try providers in order, score, prefer synced.

Rules:
- synced_only=True → reject plain results.
- duration match (when duration_s known) boosts score; mismatch beyond tolerance penalizes.
"""
from __future__ import annotations

from rapidfuzz import fuzz

from lrcdownloader.config import Settings
from lrcdownloader.core.providers.base import LrcResult


def score_result(res: LrcResult, title: str, artist: str,
                 duration_s: float = 0.0, tolerance_s: float = 5.0) -> float:
    s = res.score
    if res.synced:
        s += 0.25
    return min(1.0, s)


def text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a.lower(), b.lower()) / 100.0


def pick_best(cands: list[LrcResult], cfg: Settings) -> LrcResult | None:
    ok: list[LrcResult] = []
    for c in cands:
        if cfg.synced_only and not c.synced:
            continue
        if not cfg.allow_plain_fallback and not c.synced and cfg.synced_only:
            continue
        ok.append(c)
    if not ok:
        return None
    ok.sort(key=lambda r: (r.synced, r.score), reverse=True)
    return ok[0]


def fetch_first(providers, title: str, artist: str, album: str,
                duration_s: float, cfg: Settings) -> LrcResult | None:
    """Sequential fallback (simple, rate-limit friendly). Parallel fan-out lives in batch.py.

    Keeps the first plain result as a fallback but keeps looking for a synced
    one, so a plain LRCLIB hit does not hide a synced lrc.red/NetEase/QQ hit.
    """
    plain_fallback: LrcResult | None = None
    for p in providers:
        if p.name not in cfg.provider_order:
            continue
        try:
            res = p.search(title, artist, album, duration_s)
        except Exception:
            continue
        if res is None:
            continue
        if cfg.synced_only and not res.synced:
            continue
        res.score = score_result(res, title, artist, duration_s, cfg.duration_tolerance_s)
        if res.synced:
            return res
        if plain_fallback is None:
            plain_fallback = res
    return plain_fallback
