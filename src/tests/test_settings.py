from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest import mark, param

from public.settings import SETTINGS


class TestSettings:
    @mark.parametrize(
        ("setting", "expected"),
        [
            param(SETTINGS.network.vlan.main, 50),
            param(SETTINGS.storage.dir_.name, "local"),
            param(
                SETTINGS.storage.nfs.common.export("name"), Path("/mnt/qrt-pool/name")
            ),
            param(SETTINGS.storage.nfs.common.path("name"), Path("/mnt/name")),
            param(SETTINGS.storage.nfs.common.qrt("name"), Path("/mnt/name/qrt")),
            param(
                SETTINGS.storage.nfs.common.secrets("name"),
                Path("/mnt/name/qrt/secrets"),
            ),
            param(SETTINGS.storage.nfs.common.server, "truenas.qrt"),
            param(
                SETTINGS.storage.nfs.qrt_dataset.export,
                Path("/mnt/qrt-pool/qrt-dataset"),
            ),
            param(SETTINGS.storage.nfs.qrt_dataset.path, Path("/mnt/qrt-dataset")),
            param(SETTINGS.storage.nfs.qrt_dataset.qrt, Path("/mnt/qrt-dataset/qrt")),
            param(
                SETTINGS.storage.nfs.qrt_dataset.secrets,
                Path("/mnt/qrt-dataset/qrt/secrets"),
            ),
            param(SETTINGS.storage.nfs.qrt_dataset.name, "qrt-dataset"),
            param(SETTINGS.storage.zfspool.name, "local-zfs"),
        ],
    )
    def test_main(self, *, setting: Any, expected: Any) -> None:
        assert setting == expected

    def test_hashable(self) -> None:
        _ = hash(SETTINGS)

    def test_repr(self) -> None:
        result = repr(SETTINGS.storage)
        expected = """\
dir: local
  path /var/lib/vz
  content backup,iso,vztmpl

nfs: qrt-dataset
  path /mnt/qrt-dataset
  server truenas.qrt
  export /mnt/qrt-pool/qrt-dataset
  content backup,images,import,iso,rootdir,snippets,vztmpl
  nodes proxmox

nfs: qrt-dropbox
  path /mnt/qrt-dropbox
  server truenas.qrt
  export /mnt/qrt-pool/qrt-dropbox
  content backup,images,import,iso,rootdir,snippets,vztmpl
  nodes proxmox

nfs: isos
  path /mnt/isos
  server truenas.qrt
  export /mnt/qrt-pool/isos
  content backup,images,import,iso,rootdir,snippets,vztmpl
  nodes proxmox

zfspool: local-zfs
  pool rpool/data
  sparse
  content images,rootdir
"""
        assert result == expected

    def test_tuple(self) -> None:
        assert SETTINGS.storage.dir_.content == ("backup", "iso", "vztmpl")
