#!/usr/bin/env python3.13
import reprlib
from argparse import ArgumentParser
from dataclasses import dataclass
from logging import basicConfig, getLogger
from pathlib import Path
from subprocess import check_call

_LOGGER = getLogger(__name__)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class Settings:
    paths: list[Path]


# main


def main(settings: Settings, /) -> None:
    paths = settings.paths
    if len(paths) == 0:
        _LOGGER.info("No files to decrypt; exiting...")
        return
    _LOGGER.info(
        "Decrypting %d file%s: %s",
        len(paths),
        "s" if len(paths) >= 2 else "",
        reprlib.repr(list(map(str, paths))),
    )
    identity = Path.home().joinpath(".ssh", "id_ed25519")
    if not identity.is_file():
        raise FileNotFoundError(str(identity))
    for path in paths:
        if path.is_file() and path.suffixes[-1] == ".enc":
            _LOGGER.info("Decrypting %r...", str(path))
            new = path.with_suffix("".join(path.suffixes[:-1]))
            cmd = [
                "age",
                "--decrypt",
                f"--identity={identity}",
                f"--output={new}",
                str(path),
            ]
            check_call(cmd)
        else:
            _LOGGER.info("Skipping %r...", str(path))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="+", help="Files to encrypt")
    settings = Settings(**vars(parser.parse_args()))
    main(settings)
