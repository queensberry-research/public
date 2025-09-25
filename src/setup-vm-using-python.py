#!/usr/bin/env python3.13
from argparse import ArgumentParser
from dataclasses import dataclass
from enum import Enum, auto
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from re import search
from shutil import which
from typing import TextIO

_LOGGER = getLogger(__name__)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)

# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class Settings:
    aliases: bool = False
    bottom: bool = False


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
                raise ValueError(f"Invalid shell: {shell!r}")

    @property
    def path_rc(self) -> Path:
        return Path.home().joinpath(f".{self.name}rc")


# main


def main(settings: Settings, /) -> None:
    _LOGGER.info("Setting up VM...")
    if settings.aliases:
        _setup_aliases()
    if settings.bottom:
        _setup_bottom()


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


def _setup_bottom() -> None:
    if _has_command("btm"):
        _LOGGER.info("'bottom' is already set up")
        return
    pass


# utilities


def _has_command(cmd: str, /) -> bool:
    return which(cmd) is not None


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--aliases",
        dest="aliases",
        action="store_true",
        help="Add aliases (default: disabled)",
    )
    parser.add_argument(
        "--bottom",
        dest="bottom",
        action="store_true",
        help="Install bottom",
    )
    args = parser.parse_args()
    settings = Settings(aliases=args.aliases, bottom=args.bottom)
    main(settings)
