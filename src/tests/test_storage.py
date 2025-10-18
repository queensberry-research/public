from __future__ import annotations

from pathlib import Path

from public.storage import STORAGE_CONFIG


class TestStorageConfig:
    def test_main(self) -> None:
        assert STORAGE_CONFIG.dir_.name == "local"
        assert STORAGE_CONFIG.nfs.path == Path("/mnt/pve/qrt-share")
        assert STORAGE_CONFIG.nfs.qrt == Path("/mnt/pve/qrt-share/qrt")
        assert STORAGE_CONFIG.nfs.secrets == Path("/mnt/pve/qrt-share/qrt/secrets")
        assert STORAGE_CONFIG.zfspool.pool == Path("rpool/data")
        assert (
            str(STORAGE_CONFIG)
            == """\
dir: local
  path /var/lib/vz
  content backup,iso,vztmpl

nfs: qrt-share
  path /mnt/pve/qrt-share
  server truenas.qrt
  export /mnt/qrt-pool/qrt-dataset
  content backup,images,import,iso,rootdir,snippets,vztmpl
  nodes proxmox

zfspool: local-zfs
  pool rpool/data
  sparse
  content images,rootdir
"""
        )
