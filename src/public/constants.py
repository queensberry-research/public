from __future__ import annotations

from pathlib import Path

from .installer_constants import (
    AUTHORIZED_KEYS,
    HOME,
    KNOWN_HOSTS,
    LOCAL_BIN,
    SSH,
    SSH_CONFIG,
    XDG_CONFIG_HOME,
)

ETC = Path("/etc")


__all__ = [
    "AUTHORIZED_KEYS",
    "ETC",
    "HOME",
    "KNOWN_HOSTS",
    "LOCAL_BIN",
    "SSH",
    "SSH_CONFIG",
    "XDG_CONFIG_HOME",
]
