#!/usr/bin/env python3.13
import tarfile
from argparse import ArgumentParser
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, auto
from logging import basicConfig, getLogger
from os import environ, geteuid
from pathlib import Path
from shutil import move, which
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import assert_never
from urllib.parse import urlparse
from urllib.request import urlopen

_LOGGER = getLogger(__name__)
_BOTTOM_VERSION = "0.11.1"
_DELTA_VERSION = "0.18.2"
_DIRENV_VERSION = "2.37.1"
_JUST_VERSION = "1.42.4"
_PATH_LOCAL_BIN = Path.home().joinpath(".local", "bin")
_PATH_LOCAL_BIN.mkdir(parents=True, exist_ok=True)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class Settings:
    bottom: bool = False
    bottom_version: str = _BOTTOM_VERSION
    delta: bool = False
    delta_version: str = _DELTA_VERSION
    direnv: bool = False
    direnv_version: str = _DIRENV_VERSION
    git: bool = False
    just: bool = False
    just_version: str = _JUST_VERSION
    proxmox_apt: bool = False
    vim: bool = False

    def __post_init__(self) -> None:
        if self.git or self.vim:
            self.proxmox_apt = True


class Shell(Enum):
    bash = auto()
    zsh = auto()

    @classmethod
    def get(cls) -> "Shell":
        match Path(environ["SHELL"]).name:
            case "bash":
                return Shell.bash
            case "zsh":
                return Shell.zsh
            case shell:
                msg = f"Invalid shell: {shell!r}"
                raise ValueError(msg)

    @property
    def path_rc(self) -> Path:
        return Path.home().joinpath(f".{self.name}rc")


# main


def main(settings: Settings, /) -> None:
    _LOGGER.info("Setting up VM...")
    _setup_aliases()
    _setup_editing_mode()
    _setup_env_vars()
    if settings.proxmox_apt:
        _setup_proxmox_apt()
    if settings.bottom:
        _setup_bottom(version=settings.bottom_version)
    if settings.delta:
        _setup_delta(version=settings.delta_version)
    if settings.direnv:
        _setup_direnv(version=settings.direnv_version)
    if settings.git:
        _setup_git()
    if settings.just:
        _setup_just()
    if settings.vim:
        _setup_vim()


def _setup_aliases() -> None:
    for line in [
        """alias ~='cd "${HOME}"'""",
        """alias ..='cd ..'""",
        """alias ...='cd ../..'""",
        """alias ....='cd ../../..'""",
        """alias l='ls -al'""",
    ]:
        _append_to_rc(line)


def _setup_bottom(*, version: str = _BOTTOM_VERSION) -> None:
    if _has_command("btm"):
        _LOGGER.info("'bottom' is already set up")
        return
    _LOGGER.info("Setting up 'bottom' %s...", version)
    url = _github_url(
        "ClementTsang", "bottom", version, f"bottom_{version}-1_amd64.deb"
    )
    with _yield_download(url) as temp_file:
        cmd = ["dpkg", "-i", str(temp_file)]
        check_call(_prepend_sudo_if_not_root(cmd))


def _setup_delta(*, version: str = _DELTA_VERSION) -> None:
    if _has_command("delta"):
        _LOGGER.info("'delta' is already set up")
        return
    _LOGGER.info("Setting up 'delta' %s...", version)
    url = _github_url(
        "dandavison",
        "delta",
        version,
        f"delta-{version}-x86_64-unknown-linux-gnu.tar.gz",
    )
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        (dir_from,) = temp_dir.iterdir()
        path_from = dir_from.joinpath("delta")
        path_to = _PATH_LOCAL_BIN.joinpath("delta")
        move(path_from, path_to)


def _setup_direnv(*, version: str = _DIRENV_VERSION) -> None:
    if _has_command("direnv"):
        _LOGGER.info("'direnv' is already set up")
        return
    _LOGGER.info("Setting up 'direnv'...")
    url = _github_url("direnv", "direnv", f"v{version}", "direnv.linux-amd64")
    with _yield_download(url) as temp_file:
        path_to = _PATH_LOCAL_BIN.joinpath("direnv")
        move(temp_file, path_to)
    _append_to_rc(f"""eval "$(direnv hook {Shell.get().name})" """)


def _setup_editing_mode() -> None:
    match Shell.get():
        case Shell.bash:
            line = "set -o vi"
        case Shell.zsh:
            line = "bindkey -v"
        case never:
            assert_never(never)
    _append_to_rc(line)


def _setup_env_vars() -> None:
    _append_to_rc("""export EDITOR='nvim'""")
    _append_to_rc('''export PATH="${HOME}/.local/bin${PATH:+:${PATH}}"''')


def _setup_git() -> None:
    if _has_command("git"):
        _LOGGER.info("'git' is already set up")
        return
    _update_apt()
    _LOGGER.info("Installing 'git'...")
    check_call(_prepend_sudo_if_not_root(["apt", "install", "-y", "git"]))


def _setup_just() -> None:
    if _has_command("git"):
        _LOGGER.info("'git' is already set up")
        return
    _update_apt()
    _LOGGER.info("Installing 'git'...")
    check_call(_prepend_sudo_if_not_root(["apt", "install", "-y", "git"]))


def _setup_proxmox_apt() -> None:
    any_removed = any(
        _setup_proxmox_apt_remove(name) for name in ["ceph", "pve-enterprise"]
    )
    if any_removed:
        _update_apt()


def _setup_proxmox_apt_remove(name: str, /) -> bool:
    file = Path("/etc", "apt", "sources.list.d", f"{name}.sources")
    if file.exists():
        _LOGGER.info("Removing %r...", str(file))
        file.unlink()
        return True
    _LOGGER.info("%r is already removed", str(file))
    return False


def _setup_vim() -> None:
    if _has_command("git"):
        _LOGGER.info("'git' is already set up")
        return
    _update_apt()
    _LOGGER.info("Installing 'vim'...")
    check_call(_prepend_sudo_if_not_root(["apt", "install", "-y", "vim"]))


# utilities


def _append_to_rc(line: str, /) -> None:
    path = Shell.get().path_rc
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        _LOGGER.info("Writing %r to %r...", line, str(path))
        with path.open(mode="w") as fh:
            fh.write(f"{line}\n")
    else:
        if any(line_i == line for line_i in lines):
            _LOGGER.info("%r already in %r", line, str(path))
        else:
            _LOGGER.info("Appending %r to %r...", line, str(path))
            with path.open(mode="a") as fh:
                fh.write(f"{line}\n")


def _github_url(owner: str, repo: str, version: str, filename: str, /) -> str:
    return f"https://github.com/{owner}/{repo}/releases/download/{version}/{filename}"


def _has_command(cmd: str, /) -> bool:
    return which(cmd) is not None


def _prepend_sudo_if_not_root(cmd: list[str], /) -> list[str]:
    return cmd if _is_root() else ["sudo", *cmd]


def _is_root() -> bool:
    return geteuid() == 0


def _update_apt() -> None:
    _LOGGER.info("Updating 'apt'...")
    cmd = ["apt", "update"]
    check_call(_prepend_sudo_if_not_root(cmd))


@contextmanager
def _yield_download(url: str, /) -> Iterator[Path]:
    filename = Path(urlparse(url).path).name
    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir, filename)
        with urlopen(url) as response, temp_file.open(mode="wb") as fh:
            fh.write(response.read())
        yield temp_file


@contextmanager
def _yield_tar_gz_contents(path: Path, /) -> Iterator[Path]:
    with tarfile.open(path, "r:gz") as tf, TemporaryDirectory() as temp_dir:
        _ = tf.extractall(path=temp_dir, filter="data")
        yield Path(temp_dir)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-b",
        "--bottom",
        action="store_true",
        help="Install 'bottom' (default: %(default)s)",
    )
    parser.add_argument(
        "--bottom-version",
        default=_BOTTOM_VERSION,
        help="'bottom' version (default: %(default)s)",
    )
    parser.add_argument(
        "--delta", action="store_true", help="Install 'delta' (default: %(default)s)"
    )
    parser.add_argument(
        "--delta-version",
        default=_DELTA_VERSION,
        help="'delta' version (default: %(default)s)",
    )
    parser.add_argument(
        "--direnv", action="store_true", help="Install 'direnv' (default: %(default)s)"
    )
    parser.add_argument(
        "--direnv-version",
        default=_DIRENV_VERSION,
        help="'direnv' version (default: %(default)s)",
    )
    parser.add_argument(
        "-g", "--git", action="store_true", help="Install 'git' (default: %(default)s)"
    )
    parser.add_argument(
        "--just", action="store_true", help="Install 'just' (default: %(default)s)"
    )
    parser.add_argument(
        "--just-version",
        default=_JUST_VERSION,
        help="'just' version (default: %(default)s)",
    )
    parser.add_argument(
        "--proxmox-apt",
        action="store_true",
        help="Setup proxmox apt (default: %(default)s)",
    )
    parser.add_argument(
        "-v", "--vim", action="store_true", help="Install 'vim' (default: %(default)s)"
    )
    settings = Settings(**vars(parser.parse_args()))
    main(settings)
