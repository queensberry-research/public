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
HOME_INFRA = HOME / "infra"


RESOLV_CONF = ETC / "resolv.conf"


__all__ = [
    "AUTHORIZED_KEYS",
    "ETC",
    "HOME",
    "HOME_INFRA",
    "KNOWN_HOSTS",
    "LOCAL_BIN",
    "RESOLV_CONF",
    "SSH",
    "SSH_CONFIG",
    "XDG_CONFIG_HOME",
]
