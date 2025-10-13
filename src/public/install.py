from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from functools import wraps
from logging import basicConfig, getLogger
from pathlib import Path
from shutil import which
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, ClassVar, Literal, assert_never

if TYPE_CHECKING:
    from collections.abc import Callable

###############################################################################
# NOTE: the top-level may only contain standard library imports
###############################################################################

type _Command = Literal["init", "basic"]
type PathLike = Path | str

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
    bashrc: Path | None
    deploy_key: Path | None
    direnv_toml: Path | None
    dev: bool = False
    docker: bool = False
    skip_update_submodules: bool = False

    _flag_age_secret_key: ClassVar[str] = "--age-secret-key"  # noqa: S105
    _flag_bashrc: ClassVar[str] = "--bashrc"
    _flag_deploy_key: ClassVar[str] = "--deploy-key"
    _flag_direnv_toml: ClassVar[str] = "--direnv-toml"
    _flag_dev: ClassVar[str] = "--dev"
    _flag_docker: ClassVar[str] = "--docker"
    _flag_skip_submodule_updates: ClassVar[str] = "--skip-update-submodules"

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument(
            cls._flag_age_secret_key,
            type=cls._to_path,
            help="Path to the `age` secret key",
            metavar="PATH",
        )
        _ = parser.add_argument(
            cls._flag_bashrc,
            type=cls._to_path,
            help="Path to the `.bashrc`",
            metavar="PATH",
        )
        _ = parser.add_argument(
            cls._flag_deploy_key,
            type=cls._to_path,
            help="Path to the deploy key",
            metavar="PATH",
        )
        _ = parser.add_argument(
            cls._flag_direnv_toml,
            type=cls._to_path,
            help="Path to the `direnv.toml`",
            metavar="PATH",
        )
        _ = parser.add_argument(
            cls._flag_dev, action="store_true", help="Install development dependencies"
        )
        _ = parser.add_argument(
            cls._flag_docker, action="store_true", help="Install 'docker'"
        )
        _ = parser.add_argument(
            cls._flag_skip_submodule_updates,
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
            parts.extend([self._flag_age_secret_key, str(self.age_secret_key)])
        if self.bashrc is not None:
            parts.extend([self._flag_bashrc, str(self.bashrc)])
        if self.deploy_key is not None:
            parts.extend([self._flag_deploy_key, str(self.deploy_key)])
        if self.direnv_toml is not None:
            parts.extend([self._flag_direnv_toml, str(self.direnv_toml)])
        if self.dev:
            parts.append(self._flag_dev)
        if self.docker:
            parts.append(self._flag_docker)
        if self.skip_update_submodules:
            parts.append(self._flag_skip_submodule_updates)
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
    if which("git") is None:
        _LOGGER.info("Installing 'git'...")
        _ = check_call("apt -y update && apt install -y git", shell=True)
    with TemporaryDirectory() as _temp_dir:
        temp_dir = Path(_temp_dir)
        _LOGGER.info("Cloning repo...")
        url = "https://github.com/queensberry-research/public.git"
        _ = check_call(f"git clone {url} {temp_dir}", shell=True)
        cmd = settings.to_python_cmd("basic")
        _LOGGER.info("Running %r in %r...", cmd, str(temp_dir))
        _ = check_call(cmd, shell=True, cwd=temp_dir)


def _basic_install(settings: _Settings, /) -> None:
    ###########################################################################
    # this installer may only contain standard library & 'installer' imports
    ###########################################################################
    from public.lib import (
        install_age,
        install_bottom,
        install_curl,
        install_delta,
        install_direnv,
        install_docker,
        install_fd,
        install_fzf,
        install_jq,
        install_just,
        install_neovim,
        install_ripgrep,
        install_rsync,
        install_sops,
        install_starship,
        install_tmux,
        install_uv,
        install_vim,
        install_yq,
        setup_ssh_keys,
        setup_sshd,
    )
    from public.utilities import update_submodules

    _LOGGER.info("Basic installation...")
    if not settings.skip_update_submodules:
        _log_fail(update_submodules)()
    _log_fail(setup_ssh_keys)(
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/ssh-keys.txt"
        # TODO: change to ssh/keys.txt
    )
    _log_fail(setup_sshd)(permit_root_login=True)
    # _log_fail(_setup_subnet_env_var)() # TODO :
    _log_fail(_setup_bashrc)(bashrc=settings.bashrc)
    _log_fail(install_age)()
    _log_fail(install_curl)()
    _log_fail(install_direnv)(direnv_toml=settings.direnv_toml)
    _log_fail(install_direnv)()
    _log_fail(install_jq)()
    _log_fail(install_rsync)()
    _log_fail(install_uv)()  # after curl
    _log_fail(install_sops)(age_secret_key=settings.age_secret_key)  # after curl, jq
    # _log_fail(_install_sops_or_mkdir)(age_secret_key=age_secret_key)  # after curl, jq
    _log_fail(install_yq)()  # after curl, jq
    if docker:
        _log_fail(install_docker)()
    if dev:
        _log_fail(install_bottom)()  # after curl, jq
        _log_fail(install_delta)()
        _log_fail(install_fd)()
        _log_fail(install_fzf)()
        _log_fail(install_just)()
        _log_fail(install_neovim)(nvim_dir=_REPO_ROOT / "neovim")
        _log_fail(install_ripgrep)()
        _log_fail(install_starship)(starship_toml=_CONFIGS / "starship.toml")
        _log_fail(install_tmux)()
        _log_fail(install_vim)()


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


def _log_fail[**P](func: Callable[P, None], /) -> Callable[P, None]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            func(*args, **kwargs)
        except Exception as error:
            _LOGGER.exception(
                "Encounter %r whilst running %r", type(error).__name__, func.__name__
            )

    return wrapped


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


def _setup_bashrc(*, bashrc: PathLike | None = None) -> None:
    from public.constants import HOME
    from public.utilities import symlink_if_given

    symlink_if_given(HOME / ".bashrc", bashrc)


if __name__ == "__main__":
    _main()
