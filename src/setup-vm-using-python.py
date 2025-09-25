#!/usr/bin/env python3.13
from argparse import ArgumentParser
from dataclasses import dataclass
from enum import Enum, auto
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path

_LOGGER = getLogger(__name__)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)

# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class Settings:
    aliases: bool = False


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


def _setup_aliases() -> None:
    _LOGGER.info("Setting up aliases...")
    path = Shell.get().path_rc


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--alias",
        dest="alias",
        action="store_true",
        help="Add aliases (default: disabled)",
    )
    args = parser.parse_args()
    settings = Settings(aliases=args.alias)
    main(settings)
