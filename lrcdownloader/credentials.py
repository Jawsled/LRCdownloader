"""Secret storage: SP_DC + Spotify client creds via keyring with env fallback."""
from __future__ import annotations

import os

try:
    import keyring
except Exception:  # keyring backend may be missing on some Linux installs
    keyring = None  # type: ignore

SERVICE = "LRCdownloader"


def get_secret(name: str) -> str:
    if keyring is not None:
        try:
            v = keyring.get_password(SERVICE, name)
            if v:
                return v
        except Exception:
            pass
    return os.environ.get(name, "")


def set_secret(name: str, value: str) -> None:
    if keyring is not None:
        try:
            if value:
                keyring.set_password(SERVICE, name, value)
            else:
                keyring.delete_password(SERVICE, name)
            return
        except Exception:
            pass
