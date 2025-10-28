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

    from .types import PathLike, Subnet


###############################################################################
# standard library imports only
###############################################################################


type _Mode = Literal["public", "core", "core-in-repo", "infra", "password"]


basicConfig(
    format=f"[{{asctime}} ❯ {gethostname()} ❯ {{module}}:{{funcName}}:{{lineno}}] {{message}}",  # noqa: RUF001
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level="INFO",
)
_LOGGER = getLogger(__name__)


__version__ = "0.5.53"
_HOME_PUBLIC = Path("~/public").expanduser()
_HOME_INFRA = Path("~/infra").expanduser()
_PYTHON3_M = "python3 -m"
FLAG_PUBLIC_VERSION = "--public-version"
FLAG_INSTALLER_VERSION = "--installer-version"
FLAG_INFRA_VERSION = "--infra-version"
_FLAG_MODE = "--mode"
_FLAG_DOCKER = "--docker"
FLAG_SKIP_DEV = "--skip-dev"
_FLAG_PASSWORD = "--password"  # noqa: S105
FLAG_IB_GATEWAY_DOCKER = "--ib-gateway-docker"
FLAG_GITLAB = "--gitlab"
FLAG_GITLAB_RUNNER = "--gitlab-runner"
FLAG_POSTGRES = "--postgres"
FLAG_PYPI = "--pypi"
FLAG_REDIS = "--redis"
FLAG_DOCKER_REGISTRY = "--docker-registry"
FLAG_FORCE_RECREATE = "--force-recreate"


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _PublicInstallerSettings:
    public_version: str = __version__
    installer_version: str | None = None
    infra_version: str | None = None
    mode: _Mode | None = None
    docker: bool = False
    skip_dev: bool = False
    password: str | None = None
    ib_gateway_docker: bool = False
    gitlab: bool = False
    gitlab_runner: bool = False
    postgres: bool = False
    pypi: bool = False
    redis: bool = False
    docker_registry: bool = False
    force_recreate: bool = False

    @classmethod
    def parse(cls) -> _PublicInstallerSettings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument(
            FLAG_PUBLIC_VERSION, default=__version__, type=str, help="'public' version"
        )
        _ = parser.add_argument(
            FLAG_INSTALLER_VERSION, type=str, help="'installer' version"
        )
        _ = parser.add_argument(FLAG_INFRA_VERSION, type=str, help="'infra' version")
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
            FLAG_SKIP_DEV, action="store_true", help="Skip dev dependencies"
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
            FLAG_DOCKER_REGISTRY, action="store_true", help="Setup Docker Registry"
        )
        _ = parser.add_argument(
            FLAG_FORCE_RECREATE, action="store_true", help="Force re-create containers"
        )
        settings = _PublicInstallerSettings(**vars(parser.parse_args()))
        _LOGGER.info("'public' settings: %s", replace(settings, password="***"))  # noqa: S106
        return settings


# main


def _install() -> None:
    ###########################################################################
    # this installer may only contain standard library imports
    ###########################################################################
    _LOGGER.info("Running installer... [public=%s]", __version__)
    settings = _PublicInstallerSettings.parse()
    match settings.mode:
        case None:
            _initial_install(
                infra_version=settings.infra_version,
                public_version=settings.public_version,
                installer_version=settings.installer_version,
                docker=settings.docker,
                skip_dev=settings.skip_dev,
                ib_gateway_docker=settings.ib_gateway_docker,
                gitlab=settings.gitlab,
                gitlab_runner=settings.gitlab_runner,
                postgres=settings.postgres,
                pypi=settings.pypi,
                redis=settings.redis,
                docker_registry=settings.docker_registry,
                force_recreate=settings.force_recreate,
            )
        case "public":
            _public_install(
                public_version=settings.public_version,
                installer_version=settings.installer_version,
            )
        case "core":
            _core_install(
                public_version=settings.public_version,
                installer_version=settings.installer_version,
                infra_version=settings.infra_version,
                docker=settings.docker,
                skip_dev=settings.skip_dev,
            )
        case "core-in-repo":
            _core_install_in_repo(
                public_version=settings.public_version,
                installer_version=settings.installer_version,
                infra_version=settings.infra_version,
                docker=settings.docker,
                skip_dev=settings.skip_dev,
            )
        case "infra":
            _infra_install(
                public_version=settings.public_version,
                installer_version=settings.installer_version,
                infra_version=settings.infra_version,
                skip_dev=settings.skip_dev,
                ib_gateway_docker=settings.ib_gateway_docker,
                gitlab=settings.gitlab,
                gitlab_runner=settings.gitlab_runner,
                postgres=settings.postgres,
                pypi=settings.pypi,
                redis=settings.redis,
                docker_registry=settings.docker_registry,
                force_recreate=settings.force_recreate,
            )
        case "password":
            if settings.password is None:
                msg = "'password' must be given"
                raise ValueError(msg)
            _setup_root_password(settings.password)
        case never:
            assert_never(never)


def _initial_install(
    *,
    public_version: str = __version__,
    installer_version: str | None = None,
    infra_version: str | None = None,
    docker: bool = False,
    skip_dev: bool = False,
    ib_gateway_docker: bool = False,
    gitlab: bool = False,
    gitlab_runner: bool = False,
    postgres: bool = False,
    pypi: bool = False,
    redis: bool = False,
    docker_registry: bool = False,
    force_recreate: bool = False,
) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    desc = _append_version_descs(
        "Running initial installation",
        public=public_version,
        installer_use=installer_version,
        infra=infra_version,
    )
    _LOGGER.info("%s...", desc)
    _public_install(public_version=public_version, installer_version=installer_version)
    _core_install(
        public_version=public_version,
        installer_version=installer_version,
        infra_version=infra_version,
        docker=docker,
        skip_dev=skip_dev,
    )
    _infra_install(
        public_version=public_version,
        installer_version=installer_version,
        infra_version=infra_version,
        skip_dev=skip_dev,
        ib_gateway_docker=ib_gateway_docker,
        gitlab=gitlab,
        gitlab_runner=gitlab_runner,
        postgres=postgres,
        pypi=pypi,
        redis=redis,
        docker_registry=docker_registry,
        force_recreate=force_recreate,
    )


def _public_install(
    *, public_version: str = __version__, installer_version: str | None = None
) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    desc = _append_version_descs(
        "Running public installation",
        public=public_version,
        installer_use=installer_version,
    )
    _LOGGER.info("%s...", desc)
    _clone_repo(
        "https://github.com/queensberry-research/public.git",
        _HOME_PUBLIC,
        version=public_version,
        submodule_versions={"installer": installer_version},
    )


def _core_install(
    *,
    public_version: str = __version__,
    installer_version: str | None = None,
    infra_version: str | None = None,
    docker: bool = False,
    skip_dev: bool = False,
) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    desc = _append_version_descs(
        "Running core installation",
        public=public_version,
        installer_use=installer_version,
        infra=infra_version,
    )
    _LOGGER.info("%s...", desc)
    _update_code(
        cwd=_HOME_PUBLIC,
        version=public_version,
        submodule_versions={"installer": installer_version},
    )
    mode: _Mode = "core-in-repo"
    parts: list[str] = [
        _PYTHON3_M,
        "public.install",
        _FLAG_MODE,
        mode,
        FLAG_PUBLIC_VERSION,
        public_version,
    ]
    if installer_version is not None:
        parts.extend([FLAG_INSTALLER_VERSION, installer_version])
    if infra_version is not None:
        parts.extend([FLAG_INFRA_VERSION, infra_version])
    if docker:
        parts.append(_FLAG_DOCKER)
    if skip_dev:
        parts.append(FLAG_SKIP_DEV)
    cmd = " ".join(parts)
    _ = _run_command(cmd, env={"PYTHONPATH": "src"}, cwd=_HOME_PUBLIC)


def _core_install_in_repo(
    *,
    public_version: str = __version__,
    installer_version: str | None = None,
    infra_version: str | None = None,
    docker: bool = False,
    skip_dev: bool = False,
) -> None:
    from .constants import HOME_INFRA, HOME_PUBLIC
    from .installer_init import __version__ as installer_orig
    from .lib import (
        add_to_known_hosts,
        install_age,
        install_bottom,
        install_curl,
        install_delta,
        install_direnv,
        install_docker,
        install_fd,
        install_fzf,
        install_jq,
        install_just,
        install_neovim,
        install_ripgrep,
        install_rsync,
        install_sops,
        install_starship,
        install_tmux,
        install_uv,
        install_vim,
        setup_bashrc,
        setup_ssh,
        setup_ssh_keys,
        setup_sshd,
    )
    from .settings import PUBLIC_SETTINGS

    desc = _append_version_descs(
        "Running core installation in repo",
        public=public_version,
        installer_orig=installer_orig,
        installer_use=installer_version,
        infra=infra_version,
    )
    _LOGGER.info("%s...", desc)
    configs, subnet = _get_configs(), _get_subnet_from_ip()
    if _is_proxmox():
        _setup_proxmox_sources()
        _setup_resolv_conf()
        _setup_subnet_env_var()
    add_to_known_hosts()
    setup_bashrc(bashrc=configs / ".bashrc")
    setup_ssh(
        symlinks=[(configs / "github-infra-mirror", "github-infra-mirror")],
        templates=[
            (configs / "gitlab-full", {"subnet": subnet}),
            (configs / "gitlab-infra", {"subnet": subnet}),
        ],
    )
    _setup_ssh_deploy_keys()
    setup_ssh_keys(
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/ssh/keys.txt"
    )
    setup_sshd(permit_root_login=True)
    install_age()
    install_curl()
    install_direnv(direnv_toml=configs / "direnv.toml")
    install_jq()
    install_uv()  # after curl
    install_sops(  # after curl, jq
        age_secret_key=PUBLIC_SETTINGS.storage.nfs.qrt_dataset.secrets
        / "age/secret-key.txt"
        if _is_proxmox()
        else None
    )
    if docker:
        install_docker()
    if not skip_dev:
        install_fd()
        install_fzf()
        install_just()
        install_neovim(nvim_dir=HOME_PUBLIC / "neovim")
        install_ripgrep()
        install_rsync()
        install_starship(starship_toml=configs / "starship.toml")
        install_tmux(
            tmux_conf_oh_my_tmux=configs / ".tmux.conf",
            tmux_conf_local=configs / "tmux.conf.local",
        )
        install_vim()
        install_bottom()  # after curl, jq
        install_delta()  # after curl, jq
    _clone_repo(
        "ssh://git@github-infra-mirror/queensberry-research/infra-mirror",
        HOME_INFRA,
        version=infra_version,
        submodule_versions={"public": public_version, "installer": installer_version},
    )


def _infra_install(
    *,
    public_version: str = __version__,
    installer_version: str | None = None,
    infra_version: str | None = None,
    skip_dev: bool = False,
    ib_gateway_docker: bool = False,
    gitlab: bool = False,
    gitlab_runner: bool = False,
    postgres: bool = False,
    pypi: bool = False,
    redis: bool = False,
    docker_registry: bool = False,
    force_recreate: bool = False,
) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    desc = _append_version_descs(
        "Running 'infra.install'",
        public=public_version,
        installer_use=installer_version,
        infra=infra_version,
    )
    _LOGGER.info("%s...", desc)
    _update_code(
        cwd=_HOME_INFRA,
        version=infra_version,
        submodule_versions={"public": public_version, "installer": installer_version},
    )
    parts: list[str] = [
        _PYTHON3_M,
        "infra.install",
        FLAG_PUBLIC_VERSION,
        public_version,
    ]
    if installer_version is not None:
        parts.extend([FLAG_INSTALLER_VERSION, installer_version])
    if infra_version is not None:
        parts.extend([FLAG_INFRA_VERSION, infra_version])
    if skip_dev:
        parts.append(FLAG_SKIP_DEV)
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
    if docker_registry:
        parts.append(FLAG_DOCKER_REGISTRY)
    if force_recreate:
        parts.append(FLAG_FORCE_RECREATE)
    cmd = " ".join(parts)
    _ = _run_command(cmd, direnv=True, cwd=_HOME_INFRA)


def _setup_root_password(password: str, /) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    _LOGGER.info("Setting root password...")
    _ = _run_command(f"echo 'root:{password}' | chpasswd", skip_log=True)


# utilities - standard library


def _clone_repo(
    url: str,
    target: PathLike,
    /,
    *,
    version: str | None = None,
    submodule_versions: Mapping[str, str | None] | None = None,
) -> None:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    if which("git") is None:
        _LOGGER.info("Installing 'git'...")
        _ = _run_commands("apt -y update", "apt install -y git")
    target = Path(target)
    if target.exists():
        _LOGGER.info("%r already exists", str(target))
    else:
        _LOGGER.info("Cloning %r to %r...", url, str(target))
        _ = _run_command(f"git clone --recurse-submodules {url} {target}")
    _update_code(cwd=target, version=version, submodule_versions=submodule_versions)


def _run_commands(
    *cmds: str,
    bashrc: bool = False,
    direnv: bool = False,
    env: Mapping[str, str] | None = None,
    cwd: PathLike | None = None,
    skip_log: bool = False,
) -> list[str]:
    ###########################################################################
    # standard library imports only
    ###########################################################################
    return [
        _run_command(
            cmd, bashrc=bashrc, direnv=direnv, env=env, cwd=cwd, skip_log=skip_log
        )
        for cmd in cmds
    ]


def _run_command(
    cmd: str,
    /,
    *,
    bashrc: bool = False,
    direnv: bool = False,
    env: Mapping[str, str] | None = None,
    cwd: PathLike | None = None,
    skip_log: bool = False,
) -> str:
    ###########################################################################
    # standard library imports only
    ###########################################################################
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
    ).rstrip("\n")


# utilities - standard library & public


def _append_version_descs(
    text: str,
    /,
    *,
    public: str = __version__,
    installer_orig: str | None = None,
    installer_use: str | None = None,
    infra: str | None = None,
) -> str:
    override = "" if public == __version__ else f"->{public}"
    text = f"{text} [public={__version__}{override}]"
    match installer_orig, installer_use:
        case None, None:
            pass
        case str(), None:
            text = f"{text} [installer={installer_orig}]"
        case None, str():
            text = f"{text} [installer={installer_use}]"
        case str(), str():
            text = f"{text} [installer={installer_orig}->{installer_use}]"
        case never:
            assert_never(never)
    if infra is not None:
        text = f"{text} [infra={infra}]"
    return text


def _get_configs() -> Path:
    from .constants import HOME_PUBLIC

    return HOME_PUBLIC / "configs"


def _get_subnet_from_ip() -> Subnet:
    from .settings import PUBLIC_SETTINGS

    try:
        subnet = environ["SUBNET"]
    except KeyError:
        with socket(AF_INET, SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 80))
            ip = IPv4Address(s.getsockname()[0])
        _, _, third, _ = str(ip).split(".")
        third = int(third)
        if third == PUBLIC_SETTINGS.network.vlan.main:
            return "main"
        if third == PUBLIC_SETTINGS.network.vlan.test:
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
    from .installer_utilities import apt_update, rm

    _LOGGER.info("Setting up Proxmox sources...")
    sources = ETC / "apt/sources.list.d"

    def func(name: str, /) -> bool:
        path = sources / f"{name}.sources"
        if path.exists():
            rm(path)
            return True
        return False

    removed = list(map(func, ["ceph", "pve-enterprise"]))  # run both
    if any(removed):
        apt_update()


def _setup_resolv_conf() -> None:
    from .constants import RESOLV_CONF
    from .installer_utilities import write_template
    from .settings import PUBLIC_SETTINGS

    _LOGGER.info("Setting up 'resolv.conf'...")
    path_from = _get_configs() / "resolv.conf"
    match subnet := _get_subnet_from_ip():
        case "main":
            n = PUBLIC_SETTINGS.network.vlan.main
        case "test":
            n = PUBLIC_SETTINGS.network.vlan.test
        case never:
            assert_never(never)
    write_template(path_from, RESOLV_CONF, immutable=True, n=n, subnet=subnet)


def _setup_ssh_deploy_keys() -> None:
    from .constants import SSH
    from .installer_utilities import cp
    from .settings import PUBLIC_SETTINGS

    _LOGGER.info("Setting up deploy keys...")
    cp(
        PUBLIC_SETTINGS.storage.nfs.qrt_dataset.secrets / "deploy-keys/infra",
        SSH / "infra",
    )


def _setup_subnet_env_var() -> None:
    from .constants import BASHRC_D__SUBNET_SH
    from .installer_utilities import write_template

    path_from = _get_configs() / "subnet.sh"
    subnet = _get_subnet_from_ip()
    write_template(path_from, BASHRC_D__SUBNET_SH, subnet=subnet)


def _update_code(
    *,
    cwd: PathLike | None = None,
    version: str | None = None,
    submodule_versions: Mapping[str, str | None] | None = None,
) -> None:
    desc = "Updating code"
    if cwd is not None:
        desc = f"{desc} [cwd={cwd}]"
    if version is not None:
        desc = f"{desc} [version={version}]"
    if submodule_versions is not None:
        for sub_name, sub_version in submodule_versions.items():
            if sub_version is not None:
                desc = f"{desc} [{sub_name}={sub_version}]"
    _LOGGER.info("%s...", desc)
    reset_pull = "git checkout --force $(git symbolic-ref refs/remotes/origin/HEAD --short | sed ''s#origin/##'') && git pull --ff-only --force --prune --tags"
    _ = _run_commands(
        reset_pull,
        "git submodule update --init --recursive",
        f"git submodule foreach --recursive '{reset_pull}'",
        cwd=cwd,
    )
    if version is not None:
        _ = _run_command(f"git checkout {version}", cwd=cwd)
    if submodule_versions is not None:
        for sub_name, sub_version in submodule_versions.items():
            if sub_version is not None:
                sub_path = _run_command(
                    f"git submodule status | awk '$2 ~ /{sub_name}/ {{print $2}}'",
                    cwd=cwd,
                ).rstrip("\n")
                _ = _run_command(f"git -C {sub_path} checkout {sub_version}", cwd=cwd)


# remote


def curl_public_install(
    *,
    public_version: str = __version__,
    installer_version: str | None = None,
    infra_version: str | None = None,
    mode: _Mode | None = None,
    docker: bool = False,
    skip_dev: bool = False,
    password: str | None = None,
    ib_gateway_docker: bool = False,
    gitlab: bool = False,
    gitlab_runner: bool = False,
    postgres: bool = False,
    pypi: bool = False,
    redis: bool = False,
    docker_registry: bool = False,
    force_recreate: bool = False,
) -> str:
    parts: list[str] = [FLAG_PUBLIC_VERSION, public_version]
    if installer_version is not None:
        parts.extend([FLAG_INSTALLER_VERSION, installer_version])
    if infra_version is not None:
        parts.extend([FLAG_INFRA_VERSION, infra_version])
    if mode is not None:
        parts.extend([_FLAG_MODE, mode])
    if docker:
        parts.append(_FLAG_DOCKER)
    if skip_dev:
        parts.append(FLAG_SKIP_DEV)
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
    if docker_registry:
        parts.append(FLAG_DOCKER_REGISTRY)
    if force_recreate:
        parts.append(FLAG_FORCE_RECREATE)
    cmd = " ".join(parts)
    return f"""{{ command -v curl >/dev/null 2>&1 || {{ apt -y update && apt -y install curl; }}; }}; curl -fsLS https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/public/install.py | python3 - {cmd}"""


__all__ = [
    "FLAG_DOCKER_REGISTRY",
    "FLAG_FORCE_RECREATE",
    "FLAG_GITLAB",
    "FLAG_GITLAB_RUNNER",
    "FLAG_IB_GATEWAY_DOCKER",
    "FLAG_INFRA_VERSION",
    "FLAG_INSTALLER_VERSION",
    "FLAG_POSTGRES",
    "FLAG_PUBLIC_VERSION",
    "FLAG_PYPI",
    "FLAG_REDIS",
    "FLAG_SKIP_DEV",
    "curl_public_install",
]


if __name__ == "__main__":
    _install()
