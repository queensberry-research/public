from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import override


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageConfig:
    dir_: _StorageDirConfig = field(default_factory=lambda: _StorageDirConfig())
    nfs: _StorageNFSConfig = field(default_factory=lambda: _StorageNFSConfig())
    zfspool: _StorageZFSPoolConfig = field(
        default_factory=lambda: _StorageZFSPoolConfig()
    )

    @override
    def __repr__(self) -> str:
        return "\n".join(map(repr, [self.dir_, self.nfs, self.zfspool]))


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageDirConfig:
    name: str = "local"
    path: Path = Path("/var/lib/vz")
    content: tuple[str, ...] = ("backup", "iso", "vztmpl")

    @override
    def __repr__(self) -> str:
        return f"""\
dir: {self.name}
  path {self.path}
  content {",".join(self.content)}
"""


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageNFSConfig:
    name: str = "qrt-share"
    path: Path = Path("/mnt/pve/qrt-share")
    server: str = "truenas.qrt"
    export: Path = Path("/mnt/qrt-pool/qrt-dataset")
    content: tuple[str, ...] = (
        "backup",
        "images",
        "import",
        "iso",
        "rootdir",
        "snippets",
        "vztmpl",
    )
    nodes: tuple[str, ...] = ("proxmox",)

    @override
    def __repr__(self) -> str:
        return f"""\
nfs: {self.name}
  path {self.path}
  server {self.server}
  export {self.export}
  content {",".join(self.content)}
  nodes {",".join(self.nodes)}
"""


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageZFSPoolConfig:
    name: str = "local-zfs"
    pool: Path = Path("rpool/data")
    sparse: bool = True
    content: tuple[str, ...] = ("images", "rootdir")

    @override
    def __repr__(self) -> str:
        return f"""\
zfspool: {self.name}
  pool {self.pool}
  {"sparse" if self.sparse else ""}
  content {",".join(self.content)}
"""


STORAGE_CONFIG = _StorageConfig()


__all__ = ["STORAGE_CONFIG"]
