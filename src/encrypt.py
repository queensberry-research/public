#!/usr/bin/env python3.13
from __future__ import annotations

import reprlib
from argparse import ArgumentParser
from contextlib import contextmanager
from dataclasses import dataclass
from logging import basicConfig, getLogger
from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import urlopen

if TYPE_CHECKING:
    from collections.abc import Iterator

_LOGGER = getLogger(__name__)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    paths: list[Path]

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument(
            "paths", type=Path, nargs="+", help="Files to encrypt", metavar="PATHS"
        )
        return _Settings(**vars(parser.parse_args()))


# main


def main() -> None:
    settings = _Settings.parse()
    paths = settings.paths
    if len(paths) == 0:
        _LOGGER.info("No files to encrypt; exiting...")
        return
    _LOGGER.info(
        "Encrypting %d file%s: %s",
        len(paths),
        "s" if len(paths) >= 2 else "",
        reprlib.repr(list(map(str, paths))),
    )
    url = "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/ssh-keys.txt"
    with _yield_download(url) as temp_file:
        for path in paths:
            if path.is_file():
                _LOGGER.info("Encrypting %r...", str(path))
                new = path.with_name(f"{path.name}.enc")
                cmd = [
                    "age",
                    "--encrypt",
                    f"--recipients-file={temp_file}",
                    f"--output={new}",
                    str(path),
                ]
                check_call(cmd)
            else:
                _LOGGER.info("Skipping %r...", str(path))


# utilities


@contextmanager
def _yield_download(url: str, /) -> Iterator[Path]:
    filename = Path(urlparse(url).path).name
    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir, filename)
        with urlopen(url) as response, temp_file.open(mode="wb") as fh:
            fh.write(response.read())
        yield temp_file


if __name__ == "__main__":
    main()
