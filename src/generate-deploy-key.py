#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from getpass import getuser
from logging import basicConfig, getLogger
from pathlib import Path
from socket import gethostname
from subprocess import check_call
from time import sleep

_LOGGER = getLogger(__name__)
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    key_name: str
    host_name: str
    repo_name: str

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument(
            "-k",
            "--key",
            type=str,
            required=True,
            help="Name of the deploy key",
            metavar="STR",
            dest="key_name",
        )
        parser.add_argument(
            "-h",
            "--host",
            default="github.com",
            type=str,
            help="Name of the host",
            metavar="STR",
            dest="host_name",
        )
        parser.add_argument(
            "-r",
            "--repo",
            type=str,
            required=True,
            help="Name of the repo to clone",
            metavar="STR",
        )
        return _Settings(**vars(parser.parse_args()))


# main


def main() -> None:
    settings = _Settings.parse()

    _LOGGER.info("Generating SSH key pair...")
    private = _get_private_key(settings.key_name)
    _generate_key(private)
    public = private.with_name(f"{private.name}.pub")
    _LOGGER.info("Your public key is:\n\t%s", public.read_text())
    _append_to_config(settings.key_name, settings.host_name)
    _wait_for_user()
    _clone_repo(settings.key_name, settings.repo_name)


def _get_private_key(key_name: str, /) -> Path:
    name = f"deploy-key-{key_name}"
    return Path.home().joinpath(".ssh", name)


def _generate_key(path: Path, /) -> None:
    comment = f"{getuser()}@{gethostname()}"
    check_call([
        "ssh-keygen",
        "-f",
        str(path),
        "-N",
        "''",
        "-t",
        "ed25519",
        "-C",
        comment,
    ])


def _append_to_config(key_name: str, host_name: str, /) -> None:
    path_config = Path.home().joinpath(".ssh", "config")
    path_key = _get_private_key(key_name)
    text = f"""\


Host {key_name}
    HostName ${host_name}
    User git
    IdentityFile {path_key}
    IdentitiesOnly yes
"""
    with path_config.open(mode="a") as fh:
        _ = fh.write(text)


def _wait_for_user() -> None:
    while True:
        if input("Continue? [y]/n ") in {"", "y"}:
            return
        sleep(1.0)


def _clone_repo(key_name: str, repo_name: str, /) -> None:
    _LOGGER.info("Using %r to clone %r...", key_name, repo_name)
    check_call([
        "git",
        "clone",
        "--recurse-submodules",
        f"git@{key_name}:{repo_name}.git",
    ])


if __name__ == "__main__":
    main()
