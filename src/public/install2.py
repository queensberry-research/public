from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from shutil import which
from socket import gethostname
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING, ClassVar, assert_never

if TYPE_CHECKING:
    from collections.abc import Mapping
    from os import PathLike

basicConfig(
    format=f"[{{asctime}} ❯ {gethostname()} ❯ {{module}}:{{funcName}}:{{lineno}}] {{message}}",  # noqa: RUF001
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level="INFO",
)
_LOGGER = getLogger(__name__)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _PublicInstallerSettings:
    # classvars
    default_non_root_username: ClassVar[str] = "nonroot"

    # fields

    root_password: str | None = None
    non_root_username: str = default_non_root_username
    non_root_password: str | None = None
    docker: bool = False
    skip_dev: bool = False

    @property
    def home(self) -> Path:
        return Path(f"/home/{self.non_root_username}")

    @classmethod
    def parse(cls) -> _PublicInstallerSettings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument(
            "-rp", "--root-password", type=str, help="'root' password"
        )
        _ = parser.add_argument(
            "-u",
            "--non-root-username",
            default=cls.default_non_root_username,
            type=str,
            help="Non-root username",
        )
        _ = parser.add_argument(
            "-p", "--non-root-password", type=str, help="Non-root password"
        )
        _ = parser.add_argument(
            "-d", "--docker", action="store_true", help="Install Docker"
        )
        _ = parser.add_argument(
            "-s", "--skip-dev", action="store_true", help="Skip dev dependencies"
        )
        return _PublicInstallerSettings(**vars(parser.parse_args()))


# main


def _install() -> None:
    settings = _PublicInstallerSettings.parse()
    _set_root_password(password=settings.root_password)
    _create_user(settings.non_root_username, password=settings.non_root_password)


def _set_root_password(*, password: str | None = None) -> None:
    if password is None:
        _LOGGER.info("Skipping the setting of 'root' password...")
        return
    _LOGGER.info("Setting 'root' password...")
    _ = _run_command(f"echo 'root:{password}' | chpasswd", skip_log=True)


def _create_user(username: str, /, *, password: str | None = None) -> None:
    try:
        _ = _run_command(f"id -u {username}", skip_log=True)
    except CalledProcessError:
        _LOGGER.info("Creating %r...", username)
        _ = _run_commands(
            f"useradd --create-home --shell /bin/bash {username}",
            f"usermod -aG sudo {username}",
        )
    else:
        _LOGGER.info("%r already exists", username)
    if password is None:
        _LOGGER.info("Skipping the setting of %r password...", username)
        return
    _LOGGER.info("Setting %r password...", username)
    _ = _run_command(f"echo '{username}:{password}' | chpasswd", skip_log=True)


# utilities


def _run_commands(
    *cmds: str,
    bashrc: bool = False,
    direnv: bool = False,
    cwd: PathLike | None = None,
    env: Mapping[str, str] | None = None,
    user: str | None = None,
    skip_log: bool = False,
) -> list[str]:
    return [
        _run_command(
            cmd,
            bashrc=bashrc,
            direnv=direnv,
            env=env,
            cwd=cwd,
            user=user,
            skip_log=skip_log,
        )
        for cmd in cmds
    ]


def _run_command(
    cmd: str,
    /,
    *,
    bashrc: bool = False,
    direnv: bool = False,
    cwd: PathLike | None = None,
    env: Mapping[str, str] | None = None,
    user: str | None = None,
    skip_log: bool = False,
) -> str:
    desc = f"Running {cmd!r}"
    source_bashrc = "if [ -f ~/.bashrc ]; then source ~/.bashrc; fi"
    match bashrc, direnv:
        case False, False:
            ...
        case True, False:
            desc = f"{desc} [bashrc]"
            cmd = f"{source_bashrc}; {cmd}"
        case _, True:
            desc = f"{desc} [direnv]"
            eval_direnv_export = 'if command -v direnv >/dev/null 2>&1; then eval "$(direnv export bash)"; fi'
            cmd = f"{source_bashrc}; {eval_direnv_export}; {cmd}"
        case never:
            assert_never(never)
    if cwd is not None:
        desc = f"{desc} [cwd={cwd}]"
    if env is None:
        env_use = None
    else:
        env_use = {**environ, **env}
        desc = f"{desc} [env={env}]"
    if user is not None:
        desc = f"{desc} [user={user}]"
    if not skip_log:
        _LOGGER.info("%s...", desc)
    return check_output(
        cmd,
        executable=which("bash"),
        shell=True,
        cwd=cwd,
        env=env_use,
        text=True,
        user=user,
    ).rstrip("\n")


if __name__ == "__main__":
    _install()
