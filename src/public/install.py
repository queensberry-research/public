from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass, replace
from ipaddress import IPv4Address
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from re import search
from shutil import which
from socket import AF_INET, SOCK_DGRAM, gethostname, socket
from subprocess import check_output
from typing import TYPE_CHECKING, Literal, assert_never, get_args

if TYPE_CHECKING:
    from collections.abc import Mapping

###############################################################################
# standard library imports only
###############################################################################


type _Mode = Literal[
    "public", "core", "core-in-repo", "dev", "dev-in-repo", "infra", "password"
]
type _PathLike = Path | str
_LOGGER = getLogger(__name__)
_HOME_PUBLIC = Path("~/public").expanduser()
_HOME_INFRA = Path("~/infra").expanduser()
_PYTHON3_M = "python3 -m"
_PYTHON3_M_PUBLIC = f"{_PYTHON3_M} public.install"
_FLAG_MODE = "--mode"
_FLAG_DEV = "--dev"
_FLAG_DOCKER = "--docker"
_FLAG_PASSWORD = "--password"  # noqa: S105
FLAG_IB_GATEWAY_DOCKER = "--ib-gateway-docker"
FLAG_GITLAB = "--gitlab"
FLAG_GITLAB_RUNNER = "--gitlab-runner"
FLAG_POSTGRES = "--postgres"
FLAG_PYPI = "--pypi"
FLAG_REDIS = "--redis"
FLAG_FORCE_RECREATE = "--force-recreate"


basicConfig(
    format=f"[{{asctime}} ❯ {gethostname()} ❯ {{module}}:{{funcName}}:{{lineno}}] {{message}}",  # noqa: RUF001
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level="INFO",
)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _PublicInstallerSettings:
    mode: _Mode | None = None
    docker: bool = False
    dev: bool = False
    password: str | None = None
    ib_gateway_docker: bool = False
    gitlab: bool = False
    gitlab_runner: bool = False
    postgres: bool = False
    pypi: bool = False
    redis: bool = False
    force_recreate: bool = False

    @classmethod
    def parse(cls) -> _PublicInstallerSettings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument(
            _FLAG_MODE,
            type=str,
            choices=get_args(_Mode.__value__),
            help="Installation mode",
        )
        _ = parser.add_argument(
            _FLAG_DOCKER, action="store_true", help="Install 'docker'"
        )
        _ = parser.add_argument(
            _FLAG_DEV, action="store_true", help="Install development dependencies"
        )
        _ = parser.add_argument(_FLAG_PASSWORD, type=str, help="Root password")
        _ = parser.add_argument(
            FLAG_IB_GATEWAY_DOCKER, action="store_true", help="Setup IB Gateway Docker"
        )
        _ = parser.add_argument(FLAG_GITLAB, action="store_true", help="Setup GitLab")
        _ = parser.add_argument(
            FLAG_GITLAB_RUNNER, action="store_true", help="Setup GitLab runner"
        )
        _ = parser.add_argument(
            FLAG_POSTGRES, action="store_true", help="Setup Postgres"
        )
        _ = parser.add_argument(FLAG_PYPI, action="store_true", help="Setup PyPI")
        _ = parser.add_argument(FLAG_REDIS, action="store_true", help="Setup Redis")
        _ = parser.add_argument(
            FLAG_FORCE_RECREATE, action="store_true", help="Force re-create containers"
        )
        settings = _PublicInstallerSettings(**vars(parser.parse_args()))
        _LOGGER.info("'public' settings: %s", replace(settings, password="***"))  # noqa: S106
        return settings


# main


def _install() -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    _LOGGER.info("'public' version: 0.4.173")
    settings = _PublicInstallerSettings.parse()
    match settings.mode:
        case None:
            _initial_install(settings)
        case "public":
            _public_install()
        case "core":
            _core_install(docker=settings.docker)
        case "core-in-repo":
            _core_install_in_repo(docker=settings.docker)
        case "dev":
            _dev_install()
        case "dev-in-repo":
            _dev_install_in_repo()
        case "infra":
            _infra_install(
                ib_gateway_docker=settings.ib_gateway_docker,
                gitlab=settings.gitlab,
                gitlab_runner=settings.gitlab_runner,
                postgres=settings.postgres,
                pypi=settings.pypi,
                redis=settings.redis,
                force_recreate=settings.force_recreate,
            )
        case "password":
            if settings.password is None:
                msg = "'password' must be given"
                raise ValueError(msg)
            _setup_root_password(settings.password)
        case never:
            assert_never(never)


def _initial_install(settings: _PublicInstallerSettings, /) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    _LOGGER.info("Running initial installation...")
    _public_install()
    _core_install(docker=settings.docker)
    _LOGGER.info("Finished running initial installation")
    _infra_install(
        ib_gateway_docker=settings.ib_gateway_docker,
        gitlab=settings.gitlab,
        gitlab_runner=settings.gitlab_runner,
        postgres=settings.postgres,
        pypi=settings.pypi,
        redis=settings.redis,
        force_recreate=settings.force_recreate,
    )


def _public_install() -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    _LOGGER.info("Cloning 'public'...")
    _clone_repo("https://github.com/queensberry-research/public.git", _HOME_PUBLIC)
    _LOGGER.info("Finished cloning 'public'")


def _core_install(*, docker: bool = False) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    mode: _Mode = "core-in-repo"
    parts: list[str] = [f"{_PYTHON3_M_PUBLIC} {_FLAG_MODE} {mode}"]
    if docker:
        parts.append(_FLAG_DOCKER)
    cmd = " ".join(parts)
    _update_code(cwd=_HOME_PUBLIC)
    _ = _run_command(cmd, env={"PYTHONPATH": "src"}, cwd=_HOME_PUBLIC)


def _core_install_in_repo(*, docker: bool = False) -> None:
    from .constants import HOME_INFRA
    from .lib import (
        add_to_known_hosts,
        install_age,
        install_curl,
        install_direnv,
        install_docker,
        install_jq,
        install_sops,
        install_starship,
        install_uv,
        install_yq,
        setup_bashrc,
        setup_ssh,
        setup_ssh_keys,
        setup_sshd,
    )
    from .utilities import log_installer_version

    _LOGGER.info("Running core installation...")
    log_installer_version()
    if _is_proxmox():
        _setup_proxmox_sources()
        _setup_resolv_conf()
        _setup_subnet_env_var()
    add_to_known_hosts()
    setup_bashrc(bashrc=_get_configs() / ".bashrc")
    setup_ssh(
        symlinks=[(_get_configs() / "github-infra-mirror", "github-infra-mirror")],
        templates=[
            (_get_configs() / "gitlab-full", {"subnet": _get_subnet()}),
            (_get_configs() / "gitlab-infra", {"subnet": _get_subnet()}),
        ],
    )
    _setup_ssh_deploy_key()
    setup_ssh_keys(
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/ssh/keys.txt"
    )
    setup_sshd(permit_root_login=True)
    install_age()
    install_curl()
    install_direnv(direnv_toml=_get_configs() / "direnv.toml")
    install_jq()
    install_starship(starship_toml=_get_configs() / "starship.toml")
    install_uv()  # after curl
    install_sops(  # after curl, jq
        age_secret_key=_get_qrt_secrets() / "age/secret-key.txt"
        if _is_proxmox()
        else None
    )
    install_yq()  # after curl, jq
    if docker:
        install_docker()
    _clone_repo(
        "ssh://git@github-infra-mirror/queensberry-research/infra-mirror", HOME_INFRA
    )
    _LOGGER.info("Finished running core installation")


def _dev_install() -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    mode: _Mode = "dev-in-repo"
    cmd = f"{_PYTHON3_M_PUBLIC} {_FLAG_MODE} {mode}"
    _update_code(cwd=_HOME_PUBLIC)
    _ = _run_command(cmd, env={"PYTHONPATH": "src"}, cwd=_HOME_PUBLIC)


def _dev_install_in_repo() -> None:
    from .constants import HOME_PUBLIC
    from .lib import (
        install_bottom,
        install_delta,
        install_fd,
        install_fzf,
        install_just,
        install_neovim,
        install_ripgrep,
        install_rsync,
        install_tmux,
        install_vim,
    )
    from .utilities import log_installer_version

    _LOGGER.info("Running dev installation...")
    log_installer_version()
    install_bottom()  # after curl, jq
    install_delta()  # after curl, jq
    install_fd()
    install_fzf()
    install_just()
    install_neovim(nvim_dir=HOME_PUBLIC / "neovim")
    install_ripgrep()
    install_rsync()
    install_tmux(
        tmux_conf_oh_my_tmux=_get_configs() / ".tmux.conf",
        tmux_conf_local=_get_configs() / "tmux.conf.local",
    )
    install_vim()
    _LOGGER.info("Finished running dev installation")


def _infra_install(
    *,
    ib_gateway_docker: bool = False,
    gitlab: bool = False,
    gitlab_runner: bool = False,
    postgres: bool = False,
    pypi: bool = False,
    redis: bool = False,
    force_recreate: bool = False,
) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    _LOGGER.info("Running 'infra.install'...")
    parts: list[str] = [_PYTHON3_M, "infra.install"]
    if ib_gateway_docker:
        parts.append(FLAG_IB_GATEWAY_DOCKER)
    if gitlab:
        parts.append(FLAG_GITLAB)
    if gitlab_runner:
        parts.append(FLAG_GITLAB_RUNNER)
    if postgres:
        parts.append(FLAG_POSTGRES)
    if pypi:
        parts.append(FLAG_PYPI)
    if redis:
        parts.append(FLAG_REDIS)
    if force_recreate:
        parts.append(FLAG_FORCE_RECREATE)
    cmd = " ".join(parts)
    _update_code(cwd=_HOME_INFRA)
    _ = _run_command(cmd, direnv=True, cwd=_HOME_INFRA)
    _LOGGER.info("Finished running 'infra.install'")


def _setup_root_password(password: str, /) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    _LOGGER.info("Setting root password...")
    _ = _run_command(f"echo 'root:{password}' | chpasswd", skip_log=True)
    _LOGGER.info("Finished setting root password")


# utilities - standard library


def _clone_repo(url: str, target: _PathLike, /) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    if which("git") is None:
        _LOGGER.info("Installing 'git'...")
        _ = _run_command("apt -y update && apt install -y git")
    target = Path(target)
    if target.exists():
        _LOGGER.info("Cloning %r to %r...", url, str(target))
        _update_code(cwd=target)
    else:
        _LOGGER.info("Cloning %r to %r...", url, str(target))
        _ = _run_command(f"git clone --recurse-submodules {url} {target}")


def _run_commands(
    *cmds: str,
    direnv: bool = False,
    env: Mapping[str, str] | None = None,
    cwd: _PathLike | None = None,
    skip_log: bool = False,
) -> list[str]:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    return [
        _run_command(cmd, direnv=direnv, env=env, cwd=cwd, skip_log=skip_log)
        for cmd in cmds
    ]


def _run_command(
    cmd: str,
    /,
    *,
    direnv: bool = False,
    env: Mapping[str, str] | None = None,
    cwd: _PathLike | None = None,
    skip_log: bool = False,
) -> str:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    desc = f"Running {cmd!r}"
    if direnv:
        desc = f"{desc} [direnv]"
        cmd = f'if [ -f ~/.bashrc ]; then source ~/.bashrc; fi; if command -v direnv >/dev/null 2>&1; then eval "$(direnv export bash)" >/dev/null 2>&1; fi; {cmd}'
    if env is None:
        env_use = None
    else:
        env_use = {**environ, **env}
        desc = f"{desc} [env={env}]"
    if cwd is not None:
        desc = f"{desc} [cwd={cwd}]"
    if not skip_log:
        _LOGGER.info("%s...", desc)
    return check_output(
        cmd, executable=which("bash"), shell=True, cwd=cwd, env=env_use, text=True
    )


# utilities - standard library & public


def _get_configs() -> Path:
    from .constants import HOME_PUBLIC

    return HOME_PUBLIC / "configs"


def _get_qrt_secrets() -> Path:
    return _get_qrt_share() / "qrt/secrets"


def _get_qrt_share() -> Path:
    from .storage import STORAGE_CONFIG

    nfs = STORAGE_CONFIG.nfs
    return nfs.path if _is_proxmox() else nfs.mount_point


def _get_subnet() -> Literal["main", "test"]:
    from .constants import MAIN_SUBNET, TEST_SUBNET

    try:
        subnet = environ["SUBNET"]
    except KeyError:
        with socket(AF_INET, SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 80))
            ip = IPv4Address(s.getsockname()[0])
        _, _, third, _ = str(ip).split(".")
        third = int(third)
        if third == MAIN_SUBNET:
            return "main"
        if third == TEST_SUBNET:
            return "test"
        msg = f"Invalid IP; got {ip}"
        raise ValueError(msg) from None
    if (subnet == "main") or (subnet == "test"):  #  noqa: PLR1714
        return subnet
    msg = f"Invalid subnet; got {subnet!r}"
    raise ValueError(msg)


def _is_proxmox() -> bool:
    return bool(search("proxmox", gethostname()))


def _setup_proxmox_sources() -> None:
    from .constants import ETC
    from .utilities import apt_update, rm

    _LOGGER.info("Setting up Proxmox sources...")
    sources = ETC / "apt/sources.list.d"

    def func(name: str, /) -> bool:
        path = sources / f"{name}.sources"
        if path.exists():
            rm(path)
            return True
        _LOGGER.debug("%r is already removed", str(path))
        return False

    removed = list(map(func, ["ceph", "pve-enterprise"]))  # run both
    if any(removed):
        apt_update()


def _setup_resolv_conf() -> None:
    from .constants import MAIN_SUBNET, RESOLV_CONF, TEST_SUBNET
    from .utilities import write_template

    _LOGGER.info("Setting up 'resolv.conf'...")
    path_from = _get_configs() / "resolv.conf"
    match subnet := _get_subnet():
        case "main":
            n = MAIN_SUBNET
        case "test":
            n = TEST_SUBNET
        case never:
            assert_never(never)
    write_template(path_from, RESOLV_CONF, immutable=True, n=n, subnet=subnet)


def _setup_ssh_deploy_key() -> None:
    from .constants import SSH
    from .utilities import cp

    _LOGGER.info("Setting up Proxmox sources'...")
    cp(_get_qrt_secrets() / "deploy-key/infra", SSH / "infra")


def _setup_subnet_env_var() -> None:
    from .constants import HOME
    from .utilities import write_template

    path_from = _get_configs() / "subnet.sh"
    path_to = HOME / ".bashrc.d/subnet.sh"
    subnet = _get_subnet()
    write_template(path_from, path_to, subnet=subnet)


def _update_code(*, cwd: _PathLike | None = None) -> None:
    desc = "Updating code"
    if cwd is not None:
        desc = f"{desc} in {str(cwd)!r}"
    _LOGGER.info("%s...", desc)
    _ = _run_commands(
        "git pull",
        "git submodule update --init --recursive",
        """git submodule foreach --recursive '
            git checkout -- . &&
            git checkout $(git symbolic-ref refs/remotes/origin/HEAD | sed "s#.*/##") &&
            git pull --ff-only --force --prune --tags
        '""",
        cwd=cwd,
    )
    _LOGGER.info("Finished updating repo & submodules")


# remote


def curl_public_install(
    *,
    mode: _Mode | None = None,
    docker: bool = False,
    dev: bool = False,
    password: str | None = None,
    ib_gateway_docker: bool = False,
    gitlab: bool = False,
    gitlab_runner: bool = False,
    postgres: bool = False,
    pypi: bool = False,
    redis: bool = False,
    force_recreate: bool = False,
) -> str:
    parts: list[str] = []
    if mode is not None:
        parts.extend([_FLAG_MODE, mode])
    if docker:
        parts.append(_FLAG_DOCKER)
    if dev:
        parts.append(_FLAG_DEV)
    if password:
        parts.extend([_FLAG_PASSWORD, password])
    if ib_gateway_docker:
        parts.append(FLAG_IB_GATEWAY_DOCKER)
    if gitlab:
        parts.append(FLAG_GITLAB)
    if gitlab_runner:
        parts.append(FLAG_GITLAB_RUNNER)
    if postgres:
        parts.append(FLAG_POSTGRES)
    if pypi:
        parts.append(FLAG_PYPI)
    if redis:
        parts.append(FLAG_REDIS)
    if force_recreate:
        parts.append(FLAG_FORCE_RECREATE)
    cmd = " ".join(parts)
    return f"""{{ command -v curl >/dev/null 2>&1 || {{ apt -y update && apt -y install curl; }}; }}; curl -fsLS https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/public/install.py | python3 - {cmd}"""


__all__ = [
    "FLAG_FORCE_RECREATE",
    "FLAG_GITLAB",
    "FLAG_GITLAB_RUNNER",
    "FLAG_IB_GATEWAY_DOCKER",
    "FLAG_POSTGRES",
    "FLAG_PYPI",
    "FLAG_REDIS",
    "curl_public_install",
]


if __name__ == "__main__":
    _install()
