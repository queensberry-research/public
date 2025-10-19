from __future__ import annotations

from pathlib import Path

from public.install import (
    _get_configs,
    _get_qrt_secrets,
    _get_qrt_share,
    _get_subnet,
    _is_proxmox,
)


class TestGetConfigs:
    def test_main(self) -> None:
        assert _get_configs() == Path("~/public/configs").expanduser()


class TestGetQRTSecrets:
    def test_main(self) -> None:
        assert _get_qrt_secrets() == Path("/mnt/qrt-share/qrt/secrets")


class TestGetQRTShare:
    def test_main(self) -> None:
        assert _get_qrt_share() == Path("/mnt/qrt-share")


class TestGetSubnet:
    def test_main(self) -> None:
        assert _get_subnet() == "main"


class TestIsProxmox:
    def test_main(self) -> None:
        assert not _is_proxmox()
