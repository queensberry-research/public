from __future__ import annotations

from typing import Literal, get_args

from .installer_types import PathLike

type Subnet = Literal["qrt", "main", "test"]
SUBNETS: tuple[Subnet, ...] = get_args(Subnet.__value__)


__all__ = ["SUBNETS", "PathLike", "Subnet"]
