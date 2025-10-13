from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from logging import basicConfig, getLogger
from pathlib import Path
from typing import Literal

# from infra.constants import ETC
# from infra.installers.groups.common import install_common
# from infra.installers.utilities import apt_update, rm, update_submodules

# if TYPE_CHECKING:
#     from infra.installers.types import PathLike

_LOGGER = getLogger(__name__)
_REPO_ROOT = Path(__file__).parent


###############################################################################
# NOTE: the initial installation can only contain standard library imports
#       the post installation can also contain `infra` imports
###############################################################################


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    command: Literal["init", "post"]
    init_deploy_key: Path | None = None
    post_age_secret_key: Path | None = None
    post_dev: bool = False
    post_docker: bool = False

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        subparsers = parser.add_subparsers(dest="command", required=True)
        init = subparsers.add_parser("init", help="Initial installation")
        _ = init.add_argument(
            "init-deploy-key",
            type=cls._to_path,
            help="Path to the deploy key",
            metavar="PATH",
        )
        post = subparsers.add_parser("post", help="Post installation")
        _ = post.add_argument(
            "post-age-secret-key",
            type=cls._to_path,
            help="Path to the `age` secret key",
            metavar="PATH",
        )
        _ = post.add_argument(
            "--dev",
            action="store_true",
            help="Install development dependencies",
            dest="post_dev",
        )
        _ = post.add_argument(
            "--docker", action="store_true", help="Install 'docker'", dest="post_docker"
        )
        return _Settings(**vars(parser.parse_args()))

    @classmethod
    def _to_path(cls, text: str, /) -> Path:
        return Path(text).expanduser()


# main


def _main() -> None:
    basicConfig(
        format="{asctime} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
        level="INFO",
    )
    _LOGGER.info("Welcome")
    _Settings.parse()


def _install_deploy_key(
    *, age_secret_key: PathLike | None = None, root_password: str | None = None
) -> None:
    _LOGGER.info("Initial installation...")
    update_submodules()
    _setup_proxmox_apt()  # before `install_common`
    install_common(  # after `_setup_proxmox_apt`
        age_secret_key=age_secret_key, dev=True, root_password=root_password
    )


def _install_initial_z(
    *, age_secret_key: PathLike | None = None, root_password: str | None = None
) -> None:
    _LOGGER.info("Initial installation...")
    update_submodules()
    _setup_proxmox_apt()  # before `install_common`
    install_common(  # after `_setup_proxmox_apt`
        age_secret_key=age_secret_key, dev=True, root_password=root_password
    )


def _setup_proxmox_apt() -> None:
    sources = ETC / "apt/sources.list.d"

    def func(name: str, /) -> bool:
        path = sources / f"{name}.sources"
        if path.exists():
            rm(path)
            return True
        _LOGGER.debug("%r is already removed", str(path))
        return False

    removed = list(map(func, ["ceph", "pve-enterprise"]))  # run both
    if any(removed):
        apt_update()


if __name__ == "__main__":
    _main()
