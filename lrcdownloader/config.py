"""Central config with sane defaults (persisted as JSON in platformdirs user dir)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "LRCdownloader"
CONFIG_VERSION = 2

# Fallback order. Search-based providers are tried in this order; the first
# provider that returns an acceptable synced result wins.
DEFAULT_PROVIDER_ORDER = ["lrclib", "lrcred", "netease", "qq", "syncedlyrics", "spotify"]
KNOWN_PROVIDERS = tuple(DEFAULT_PROVIDER_ORDER)
ADDED_IN_V2 = ("lrcred", "netease", "qq")


def _merge_provider_order(order: list[str]) -> list[str]:
    """Add newly shipped providers once, preserving the user's existing order."""
    known = [p for p in order if p in KNOWN_PROVIDERS]
    for p in ADDED_IN_V2:
        if p in known:
            continue
        idx = DEFAULT_PROVIDER_ORDER.index(p)
        prev = next((q for q in reversed(DEFAULT_PROVIDER_ORDER[:idx]) if q in known), None)
        if prev is None:
            known.insert(0, p)
        else:
            known.insert(known.index(prev) + 1, p)
    return known


@dataclass
class Settings:
    config_version: int = CONFIG_VERSION
    provider_order: list[str] = field(default_factory=lambda: list(DEFAULT_PROVIDER_ORDER))
    synced_only: bool = False          # if True, never accept plain lyrics
    allow_plain_fallback: bool = True  # if False + synced_only, plain is rejected
    skip_if_sidecar: bool = True       # scan-first: skip when basename-matched .lrc exists
    # Embed-kind-aware skip: 'none' = always fetch; 'any' = skip if any embed;
    # 'synced_or_better' = skip only if embed is synced/enhanced (plain embed still fetches).
    embed_skip_mode: str = "synced_or_better"
    output_mode: str = "both"          # 'sidecar' | 'embed' | 'both'
    overwrite: str = "missing"         # 'missing' | 'never' | 'force'
    concurrency: int = 4
    timeout_s: float = 12.0
    duration_tolerance_s: float = 5.0
    spotify_api_base: str = "http://localhost:8080"  # self-hosted spotify-lyrics-api
    lrcred_contact: str = ""  # required before lrc.red is used; the UI prompts for it
    syncedlyrics_providers: list[str] = field(
        default_factory=lambda: ["NetEase", "Musixmatch", "Megalobiz", "Lrclib"]
    )
    translation_lang: str = ""  # ISO-639-1 or empty

    def path(self) -> Path:
        d = Path(user_config_dir(APP_NAME))
        d.mkdir(parents=True, exist_ok=True)
        return d / "settings.json"

    def load(self) -> "Settings":
        p = self.path()
        loaded_version = 1
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                loaded_version = int(data.get("config_version", 1) or 1)
                for k, v in data.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
                if not isinstance(self.provider_order, list):
                    self.provider_order = list(DEFAULT_PROVIDER_ORDER)
            except Exception:
                pass
        if loaded_version < CONFIG_VERSION:
            self.provider_order = _merge_provider_order(self.provider_order)
            self.config_version = CONFIG_VERSION
        return self

    def save(self) -> None:
        self.path().write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def get_settings() -> Settings:
    return Settings().load()
