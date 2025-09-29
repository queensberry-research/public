#!/usr/bin/env python3
from __future__ import annotations

from logging import basicConfig, getLogger

_LOGGER = getLogger(__name__)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)
