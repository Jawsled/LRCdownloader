"""Central config with sane defaults (persisted as JSON in platformdirs user dir)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "LRCdownloader"


@dataclass
class Settings:
    provider_order: list[str] = field(default_factory=lambda: ["lrclib", "syncedlyrics", "spotify"])
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
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
            except Exception:
                pass
        return self

    def save(self) -> None:
        self.path().write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def get_settings() -> Settings:
    return Settings().load()
