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
from re import search
from shutil import move, which
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import TextIO
from urllib.parse import urlparse
from urllib.request import urlopen

_LOGGER = getLogger(__name__)
_BOTTOM_VERSION = "0.11.1"
_DELTA_VERSION = "0.18.2"
_PATH_LOCAL_BIN = Path.home().joinpath(".local", "bin")
_PATH_LOCAL_BIN.mkdir(parents=True, exist_ok=True)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class Settings:
    aliases: bool = False
    bottom: bool = False
    bottom_version: str = _BOTTOM_VERSION
    delta: bool = False
    delta_version: str = _DELTA_VERSION


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
    if settings.aliases:
        _setup_aliases()
    if settings.bottom:
        _setup_bottom(version=settings.bottom_version)
    if settings.delta:
        _setup_delta(version=settings.delta_version)


def _setup_aliases() -> None:
    _LOGGER.info("Setting up aliases...")
    path = Shell.get().path_rc

    def append(file: TextIO, /) -> None:
        file.write("""

# aliases
alias ~='cd "${HOME}"'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias l='ls -al'
""")

    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        _LOGGER.info("Writing to %r...", str(path))
        with path.open(mode="w") as fh:
            append(fh)
    else:
        if not any(search("# aliases", line) for line in lines):
            _LOGGER.info("Appending to %r...", str(path))
            with path.open(mode="a") as fh:
                append(fh)


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
        if not _is_root():
            cmd = ["sudo", *cmd]
        check_call(cmd)  # noqa: S603


def _setup_delta(*, version: str = _DELTA_VERSION) -> None:
    if _has_command("delta") and 0:
        _LOGGER.info("'delta' is already set up")
        return
    _LOGGER.info("Setting up 'delta' %s...", version)
    stem = f"delta-{version}-x86_64-unknown-linux-gnu"
    filename = f"{stem}.tar.gz"
    url = _github_url("dandavison", "delta", version, filename)
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        (dir_from,) = temp_dir.iterdir()
        path_from = dir_from.joinpath("delta")
        path_to = _PATH_LOCAL_BIN.joinpath("delta")
        move(path_from, path_to)


# utilities


def _github_url(owner: str, repo: str, version: str, filename: str, /) -> str:
    return f"https://github.com/{owner}/{repo}/releases/download/{version}/{filename}"


def _has_command(cmd: str, /) -> bool:
    return which(cmd) is not None


def _is_root() -> bool:
    return geteuid() == 0


@contextmanager
def _yield_download(url: str, /) -> Iterator[Path]:
    filename = Path(urlparse(url).path).name
    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir, filename)
        with urlopen(url) as response, temp_file.open(mode="wb") as fh:  # noqa: S310
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
        "-a", "--aliases", action="store_true", help="Add aliases (default: disabled)"
    )
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
        "-d",
        "--delta",
        action="store_true",
        help="Install 'delta' (default: %(default)s)",
    )
    parser.add_argument(
        "--delta-version",
        default=_DELTA_VERSION,
        help="'delta' version (default: %(default)s)",
    )
    settings = Settings(**vars(parser.parse_args()))
    main(settings)
