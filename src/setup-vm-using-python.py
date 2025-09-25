#!/usr/bin/env python3
from dataclasses import dataclass


@dataclass
class Settings:
    resolv_nameservers: list[str]
    resolv_search: str
    truenas_version: str
    truenas_vmid: int
    truenas_memory: int
    truenas_cores: int
    truenas_lvm_size: int


def main() -> None:
    pass
