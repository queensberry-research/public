from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from logging import basicConfig, getLogger
from pathlib import Path
from shutil import which
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import Literal, assert_never

###############################################################################
# NOTE: the top-level may only contain standard library imports
###############################################################################

type _Command = Literal["init", "basic"]

_LOGGER = getLogger(__name__)
_REPO_ROOT = Path(__file__).parent.parent.parent
_MODULE_PATH = ".".join(
    Path(__file__).relative_to(_REPO_ROOT.joinpath("src")).with_suffix("").parts
)
_PYTHON_CMD = f"python3 -m {_MODULE_PATH}"


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    command: _Command
    age_secret_key: Path | None
    deploy_key: Path | None
    dev: bool = False
    docker: bool = False
    skip_update_submodules: bool = False

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument(
            "-a",
            "--age-secret-key",
            type=cls._to_path,
            help="Path to the `age` secret key",
            metavar="PATH",
        )
        _ = parser.add_argument(
            "-d",
            "--deploy-key",
            type=cls._to_path,
            help="Path to the deploy key",
            metavar="PATH",
        )
        _ = parser.add_argument(
            "--dev", action="store_true", help="Install development dependencies"
        )
        _ = parser.add_argument(
            "--docker", action="store_true", help="Install 'docker'"
        )
        _ = parser.add_argument(
            "--skip-update-submodules",
            action="store_true",
            help="Skip updating of the submodules",
        )
        subparsers = parser.add_subparsers(dest="command", required=True)
        cmd: _Command = "init"
        _ = subparsers.add_parser(cmd, help="Initial installation")
        cmd: _Command = "basic"
        _ = subparsers.add_parser(cmd, help="Basic installation")
        return _Settings(**vars(parser.parse_args()))

    def to_python_cmd(self, cmd: _Command, /) -> str:
        parts: list[str] = [_PYTHON_CMD, cmd]
        if self.age_secret_key is not None:
            parts.extend(["-a", str(self.age_secret_key)])
        if self.deploy_key is not None:
            parts.extend(["-d", str(self.deploy_key)])
        if self.dev:
            parts.extend(["--dev"])
        if self.docker:
            parts.extend(["--docker"])
        if self.skip_update_submodules:
            parts.extend(["--skip-update-submodules"])
        return " ".join(parts)

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
    settings = _Settings.parse()
    match settings.command:
        case "init":
            _initial_install(settings)
        case "basic":
            _basic_install(settings)
        case never:
            assert_never(never)


def _initial_install(settings: _Settings, /) -> None:
    ###########################################################################
    # this installer may only contain standard library imports
    ###########################################################################
    _LOGGER.info("Initial installation...")
    for cmd in ["curl", "git"]:
        if which(cmd) is None:
            _LOGGER.info("%r not found; installing...", cmd)
            _ = check_call(f"apt -y update && apt install -y {cmd}", shell=True)
    with TemporaryDirectory() as _temp_dir:
        temp_dir = Path(_temp_dir)
        _LOGGER.info("Cloning repo...")
        url = "https://github.com/queensberry-research/public.git"
        _ = check_call(f"git clone {url} {temp_dir}", shell=True)
        _LOGGER.info(" Cmd is %r", settings.to_python_cmd("post"))


def _basic_install(settings: _Settings, /) -> None:
    ###########################################################################
    # this installer may only contain standard library & 'installer' imports
    ###########################################################################
    from public.utilities import update_submodules

    _LOGGER.info("Basic installation...")
    if not settings.skip_update_submodules:
        update_submodules()


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


# utilities


def _setup_proxmox_apt() -> None:
    from public.more_constants import ETC
    from public.utilities import apt_update, rm

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
