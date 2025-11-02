from __future__ import annotations

from public.utilities import is_proxmox


class TestIsProxmox:
    def test_main(self) -> None:
        assert not is_proxmox()
