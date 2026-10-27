"""Prompt for the lrc.red contact email required by its API terms."""
from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

from lrcdownloader.config import Settings

_TITLE = "lrc.red contact email"
_MESSAGE = (
    "lrc.red requires apps to identify themselves with a contact email in the "
    "User-Agent.\n\n"
    "Enter an email address to use lrc.red. If you cancel, lrc.red will be "
    "skipped for this request."
)


def ensure_lrcred_contact(parent: QWidget, cfg: Settings) -> bool:
    """Return True when lrc.red is enabled and a contact email is configured."""
    if "lrcred" not in cfg.provider_order:
        return False
    if cfg.lrcred_contact.strip():
        return True

    email, ok = QInputDialog.getText(parent, _TITLE, _MESSAGE)
    if not ok:
        return False
    email = email.strip()
    if email.lower().startswith("mailto:"):
        email = email[7:].strip()
    if not email or "@" not in email:
        QMessageBox.warning(
            parent, _TITLE,
            "Please enter a valid email address. lrc.red will be skipped "
            "for this request.",
        )
        return False

    cfg.lrcred_contact = email
    cfg.save()
    return True
