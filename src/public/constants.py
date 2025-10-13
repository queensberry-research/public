from __future__ import annotations

from pathlib import Path

from .installer_constants import HOME, LOCAL_BIN, SSH, XDG_CONFIG_HOME

ETC = Path("/etc")


__all__ = ["ETC", "HOME", "LOCAL_BIN", "SSH", "XDG_CONFIG_HOME"]
