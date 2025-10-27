from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest import mark, param

from public.settings import PUBLIC_SETTINGS


class TestSettings:
    @mark.parametrize(
        ("setting", "expected"),
        [
            param(PUBLIC_SETTINGS.network.vlan.main, 50),
            param(PUBLIC_SETTINGS.storage.dir_.name, "local"),
            param(
                PUBLIC_SETTINGS.storage.nfs.common.export("name"),
                Path("/mnt/qrt-pool/name"),
            ),
            param(PUBLIC_SETTINGS.storage.nfs.common.path("name"), Path("/mnt/name")),
            param(
                PUBLIC_SETTINGS.storage.nfs.common.qrt("name"), Path("/mnt/name/qrt")
            ),
            param(
                PUBLIC_SETTINGS.storage.nfs.common.secrets("name"),
                Path("/mnt/name/qrt/secrets"),
            ),
            param(PUBLIC_SETTINGS.storage.nfs.common.server, "truenas.qrt"),
            param(
                PUBLIC_SETTINGS.storage.nfs.qrt_dataset.export,
                Path("/mnt/qrt-pool/qrt-dataset"),
            ),
            param(
                PUBLIC_SETTINGS.storage.nfs.qrt_dataset.path, Path("/mnt/qrt-dataset")
            ),
            param(
                PUBLIC_SETTINGS.storage.nfs.qrt_dataset.qrt,
                Path("/mnt/qrt-dataset/qrt"),
            ),
            param(
                PUBLIC_SETTINGS.storage.nfs.qrt_dataset.secrets,
                Path("/mnt/qrt-dataset/qrt/secrets"),
            ),
            param(PUBLIC_SETTINGS.storage.nfs.qrt_dataset.name, "qrt-dataset"),
            param(PUBLIC_SETTINGS.storage.zfspool.name, "local-zfs"),
        ],
    )
    def test_main(self, *, setting: Any, expected: Any) -> None:
        assert setting == expected

    def test_hashable(self) -> None:
        _ = hash(PUBLIC_SETTINGS)

    def test_repr(self) -> None:
        result = repr(PUBLIC_SETTINGS.storage)
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

nfs: qrt-images
  path /mnt/qrt-images
  server truenas.qrt
  export /mnt/qrt-pool/qrt-images
  content backup,images,import,iso,rootdir,snippets,vztmpl
  nodes proxmox

nfs: python-packages
  path /mnt/python-packages
  server truenas.qrt
  export /mnt/qrt-pool/python-packages
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
        assert PUBLIC_SETTINGS.storage.dir_.content == ("backup", "iso", "vztmpl")
