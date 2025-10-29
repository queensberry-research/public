from __future__ import annotations

from typing import Literal

from .installer_types import PathLike

type Subnet = Literal["qrt", "main", "test"]


__all__ = ["PathLike", "Subnet"]
