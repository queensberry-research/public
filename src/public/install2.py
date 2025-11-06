from __future__ import annotations

from getpass import getuser
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from shutil import which
from socket import gethostname
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING, assert_never

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
_NONROOT = "nonroot"
_NONROOT_HOME = Path(f"/home/{_NONROOT}")
_PASSWORD = "1234"  # noqa: S105


def _install() -> None:
    _create_user()
    # _switch_user()


def _create_user() -> None:
    try:
        _ = _run_command(f"id -u {_NONROOT}")
    except CalledProcessError:
        _LOGGER.info("Creating %r...", _NONROOT)
        _ = _run_commands(
            f"useradd --create-home --shell /bin/bash {_NONROOT}",
            f"echo '{_NONROOT}:{_PASSWORD}' | chpasswd",
            f"usermod -aG sudo {_NONROOT}",
        )
    else:
        _LOGGER.info("%r already exists", _NONROOT)
        # return
    z = _run_command("echo $(whoami)", user=_NONROOT)
    print(z)
    z = _run_command("echo $(pwd)", user=_NONROOT)
    print(z)
    z = _run_command("echo $(pwd)", cwd=_NONROOT_HOME, user=_NONROOT)
    print(z)


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
