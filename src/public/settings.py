from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import override

from .utilities import field_df, yq_bool, yq_int, yq_path, yq_str, yq_strs

_CONFIG_TOML = Path(__file__) / "public_config.toml"


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    network: _Network = field_df(lambda: _Network)
    storage: _Storage = field_df(lambda: _Storage)


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Network:
    vlan: _NetworkVLAN = field_df(lambda: _NetworkVLAN)


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _NetworkVLAN:
    main: int = yq_int(_CONFIG_TOML, ".network.vlan.main")
    test: int = yq_int(_CONFIG_TOML, ".network.vlan.test")


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Storage:
    dir_: _StorageDir = field_df(lambda: _StorageDir)
    nfs: _StorageNFS = field_df(lambda: _StorageNFS)
    zfspool: _StorageZFSPool = field_df(lambda: _StorageZFSPool)

    @override
    def __repr__(self) -> str:
        return "\n".join(map(repr, [self.dir_, self.nfs, self.zfspool]))


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageDir:
    name: str = yq_str(_CONFIG_TOML, ".storage.dir.name")
    path: Path = yq_path(_CONFIG_TOML, ".storage.dir.path")
    content: tuple[str, ...] = yq_strs(_CONFIG_TOML, ".storage.dir.content")

    @override
    def __repr__(self) -> str:
        return f"""\
dir: {self.name}
  path {self.path}
  content {",".join(self.content)}
"""


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageNFS:
    name: str = yq_str(_CONFIG_TOML, ".storage.nfs.name")
    path: Path = yq_path(_CONFIG_TOML, ".storage.nfs.path")
    server: str = yq_str(_CONFIG_TOML, ".storage.nfs.server")
    export: Path = yq_path(_CONFIG_TOML, ".storage.nfs.export")
    content: tuple[str, ...] = yq_strs(_CONFIG_TOML, ".storage.nfs.content")
    nodes: tuple[str, ...] = yq_strs(_CONFIG_TOML, ".storage.nfs.nodes")
    mount_point: Path = yq_path(_CONFIG_TOML, ".storage.nfs.mount_point")

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

    @property
    def qrt(self) -> Path:
        return self.path / "qrt"

    @property
    def secrets(self) -> Path:
        return self.qrt / "secrets"


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageZFSPool:
    name: str = yq_str(_CONFIG_TOML, ".storage.zfspool.name")
    pool: Path = yq_path(_CONFIG_TOML, ".storage.zfspool.pool")
    sparse: bool = yq_bool(_CONFIG_TOML, ".storage.zfspool.sparse")
    content: tuple[str, ...] = yq_strs(_CONFIG_TOML, ".storage.zfspool.content")

    @override
    def __repr__(self) -> str:
        return f"""\
zfspool: {self.name}
  pool {self.pool}
  {"sparse" if self.sparse else ""}
  content {",".join(self.content)}
"""


SETTINGS = _Settings()


__all__ = ["SETTINGS"]
