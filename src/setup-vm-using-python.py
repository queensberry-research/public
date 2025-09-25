#!/usr/bin/env python3.13
from argparse import ArgumentParser
from dataclasses import dataclass
from enum import Enum, auto
from logging import basicConfig, getLogger
from os import environ, geteuid
from pathlib import Path
from re import search
from shutil import which
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import TextIO
from urllib.request import urlopen

_LOGGER = getLogger(__name__)
_BOTTOM_VERSION = "0.11.1"
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)

# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class Settings:
    aliases: bool = False
    bottom: bool = False
    bottom_version: str = _BOTTOM_VERSION


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
    filename = f"bottom_{version}-1_amd64.deb"
    url = (
        f"https://github.com/ClementTsang/bottom/releases/download/{version}/{filename}"
    )
    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir, filename)
        with urlopen(url) as response, temp_file.open(mode="wb") as fh:  # noqa: S310
            fh.write(response.read())
        cmd = ["dpkg", "-i", str(temp_file)]
        if not _is_root():
            cmd = ["sudo", *cmd]
        check_call(cmd)  # noqa: S603


# utilities


def _has_command(cmd: str, /) -> bool:
    return which(cmd) is not None


def _is_root() -> bool:
    return geteuid() == 0


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-a",
        "--aliases",
        dest="aliases",
        action="store_true",
        help="Add aliases (default: disabled)",
    )
    parser.add_argument(
        "-b",
        "--bottom",
        dest="bottom",
        action="store_true",
        help="Install bottom (default: %(default)s)",
    )
    parser.add_argument(
        "--bottom-version",
        default=_BOTTOM_VERSION,
        help="Bottom version (default: %(default)s)",
    )
    args = parser.parse_args()
    settings = Settings(aliases=args.aliases, bottom=args.bottom)
    main(settings)
