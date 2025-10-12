#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import InitVar, asdict, astuple, dataclass, field, replace
from enum import StrEnum, auto
from getpass import getuser
from logging import Formatter, Handler, StreamHandler, basicConfig, getLogger
from pathlib import Path
from socket import gethostname
from subprocess import CalledProcessError, check_call, check_output, run
from time import sleep
from typing import assert_never

_LOGGER = getLogger(__name__)
_SSH = Path("~/.ssh").expanduser()


# settings


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    mode: _Mode

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument("-m", "--mode", choices=_Mode, help="Select the mode.")
        return _Settings(**vars(parser.parse_args()))


class _Mode(StrEnum):
    gitlab = "gitlab"
    github = "github"


# main


def main(mode: _Mode, /) -> None:
    _LOGGER.info("Setting up proxmox...")
    known_hosts = _SSH / "known_hosts"
    known_hosts.parent.mkdir(parents=True, exist_ok=True)
    known_hosts.touch()
    _run_commands("apt install -y git", "ssh-keyscan github.com >> ~/.ssh/known_hosts")
    match mode:
        case _Mode.github:
            asdf
        case _Mode.gitlab:
            asdf
        case never:
            assert_never(never)


# utilities


def _clone_from_github() -> None:
    _LOGGER.info("Generating deploy key...")
    private = _SSH / "deploy-key-github-infra-mirror"
    public = private.with_name(f"{private.name}.pub")
    for path in [private, public]:
        path.unlink(missing_ok=True)
    comment = f"{getuser()}@{gethostname()}"
    _run_commands(f"ssh-keygen -f {private} -t ed25519 -C {comment} -N ''")
    lines = [
        "Your public key is:",
        f"\t{public.read_text()}",
        "Add at:",
        "\tGitHub: https://github.com/queensberry-research/infra-mirror/settings/keys/new",
    ]
    _LOGGER.info("\n".join(lines))
    _wait_for_user()


def _run_commands(*cmds: str) -> None:
    for cmd in cmds:
        _LOGGER.info("Running %r...", cmd)
        _ = check_call(cmd, shell=True)


def _wait_for_user() -> None:
    while True:
        if input("Continue? [y]/n ") in {"", "y"}:
            return
        sleep(1.0)


def _write_ssh_config() -> None:
    path = _SSH / "config"


if __name__ == "__main__":
    settings = _Settings.parse()
    basicConfig(
        format="{asctime} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
        level="INFO",
    )
    main(settings.mode)
