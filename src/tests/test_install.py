from __future__ import annotations

from pathlib import Path

from public.install import _get_configs, _get_subnet_from_ip, _is_proxmox


class TestGetConfigs:
    def test_main(self) -> None:
        assert _get_configs() == Path("~/public/configs").expanduser()


class TestGetSubnet:
    def test_main(self) -> None:
        assert _get_subnet_from_ip() == "main"


class TestIsProxmox:
    def test_main(self) -> None:
        assert not _is_proxmox()
