from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import override

from .utilities import field_df, toml_bool, toml_int, toml_path, toml_str, toml_strs

_CONFIG_TOML = Path(__file__).parent / "public_config.toml"
if not _CONFIG_TOML.exists():
    raise FileNotFoundError(_CONFIG_TOML)


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    network: _Network = field_df(lambda: _Network)
    storage: _Storage = field_df(lambda: _Storage)


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Network:
    vlan: _NetworkVLAN = field_df(lambda: _NetworkVLAN)


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _NetworkVLAN:
    main: int = toml_int(_CONFIG_TOML, "network.vlan.main")
    test: int = toml_int(_CONFIG_TOML, "network.vlan.test")


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
    name: str = toml_str(_CONFIG_TOML, "storage.dir.name")
    path: Path = toml_path(_CONFIG_TOML, "storage.dir.path")
    content: tuple[str, ...] = toml_strs(_CONFIG_TOML, "storage.dir.content")

    @override
    def __repr__(self) -> str:
        return f"""\
dir: {self.name}
  path {self.path}
  content {",".join(self.content)}
"""


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageNFS:
    common: _StorageNFSCommon = field_df(lambda: _StorageNFSCommon)
    qrt_dataset: _Member = field_df(lambda: _Member.new("storage.nfs.qrt_dataset"))
    qrt_dropbox: _Member = field_df(lambda: _Member.new("storage.nfs.qrt_dropbox"))
    qrt_images: _Member = field_df(lambda: _Member.new("storage.nfs.qrt_images"))
    isos: _Member = field_df(lambda: _Member.new("storage.nfs.isos"))

    @override
    def __repr__(self) -> str:
        return "\n".join(
            map(repr, [self.qrt_dataset, self.qrt_dropbox, self.qrt_images, self.isos])
        )


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageNFSCommon:
    export_template: Path = toml_path(
        _CONFIG_TOML, "storage.nfs.common.export_template"
    )
    path_template: Path = toml_path(_CONFIG_TOML, "storage.nfs.common.path_template")
    server: str = toml_str(_CONFIG_TOML, "storage.nfs.common.server")
    content: tuple[str, ...] = toml_strs(_CONFIG_TOML, "storage.nfs.common.content")
    nodes: tuple[str, ...] = toml_strs(_CONFIG_TOML, "storage.nfs.common.nodes")

    def export(self, name: str, /) -> Path:
        common = _StorageNFSCommon()
        path = Template(str(common.export_template)).substitute(name=name)
        return Path(path)

    def path(self, name: str, /) -> Path:
        common = _StorageNFSCommon()
        path = Template(str(common.path_template)).substitute(name=name)
        return Path(path)

    def qrt(self, name: str, /) -> Path:
        return self.path(name) / "qrt"

    def secrets(self, name: str, /) -> Path:
        return self.qrt(name) / "secrets"


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _StorageZFSPool:
    name: str = toml_str(_CONFIG_TOML, "storage.zfspool.name")
    pool: Path = toml_path(_CONFIG_TOML, "storage.zfspool.pool")
    sparse: bool = toml_bool(_CONFIG_TOML, "storage.zfspool.sparse")
    content: tuple[str, ...] = toml_strs(_CONFIG_TOML, "storage.zfspool.content")

    @override
    def __repr__(self) -> str:
        return f"""\
zfspool: {self.name}
  pool {self.pool}
  {"sparse" if self.sparse else ""}
  content {",".join(self.content)}
"""


# private


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Member:
    name: str = toml_str(_CONFIG_TOML, "name")

    @classmethod
    def new(cls, path: str, /) -> type[_Member]:
        @dataclass(
            repr=False,  # else will override `repr`
            order=True,
            unsafe_hash=True,
            kw_only=True,
            slots=True,
        )
        class _Member2(_Member):
            name: str = toml_str(_CONFIG_TOML, f"{path}.name")

        return _Member2

    @override
    def __repr__(self) -> str:
        common = _StorageNFSCommon()
        return f"""\
nfs: {self.name}
  path {self.path}
  server {common.server}
  export {self.export}
  content {",".join(common.content)}
  nodes {",".join(common.nodes)}
"""

    @property
    def export(self) -> Path:
        return _StorageNFSCommon().export(self.name)

    @property
    def path(self) -> Path:
        return _StorageNFSCommon().path(self.name)

    @property
    def qrt(self) -> Path:
        return _StorageNFSCommon().qrt(self.name)

    @property
    def secrets(self) -> Path:
        return _StorageNFSCommon().secrets(self.name)


# instance


PUBLIC_SETTINGS = _Settings()


__all__ = ["PUBLIC_SETTINGS"]
