from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from ipaddress import IPv4Address
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from re import search
from shutil import copytree, which
from socket import AF_INET, SOCK_DGRAM, gethostname, socket
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Literal, assert_never

if TYPE_CHECKING:
    from collections.abc import Mapping

###############################################################################
# NOTE: the top-level may only contain standard library imports
###############################################################################


type _PathLike = Path | str
_LOGGER = getLogger(__name__)
_FLAG_POST = "--post"
_FLAG_SKIP_UPDATE_SUBMODULES = "--skip-update-submodules"
_FLAG_DOCKER = "--docker"
_FLAG_PROXMOX = "--proxmox"
FLAG_SKIP_PUBLIC = "--skip-public"
FLAG_IB_GATEWAY_DOCKER = "--ib-gateway-docker"
FLAG_GITLAB = "--gitlab"
FLAG_GITLAB_RUNNER = "--gitlab-runner"
FLAG_POSTGRES = "--postgres"
FLAG_PYPI = "--pypi"
FLAG_REDIS = "--redis"


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    post: bool = False
    skip_update_submodules: bool = False
    docker: bool = False
    proxmox: bool = False
    ib_gateway_docker: bool = False
    gitlab: bool = False
    gitlab_runner: bool = False
    postgres: bool = False
    pypi: bool = False
    redis: bool = False

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument(
            _FLAG_POST, action="store_true", help="Run the post-installation"
        )
        _ = parser.add_argument(
            _FLAG_SKIP_UPDATE_SUBMODULES,
            action="store_true",
            help="Skip the updating of the submodules",
        )
        _ = parser.add_argument(
            _FLAG_DOCKER, action="store_true", help="Install 'docker'"
        )
        _ = parser.add_argument(
            _FLAG_PROXMOX, action="store_true", help="Run the Proxmox installation"
        )
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
        return _Settings(**vars(parser.parse_args()))

    @property
    def python3_public(self) -> str:
        parts: list[str] = [
            "python3",
            "-m",
            "public.install",
            _FLAG_POST,
            _FLAG_SKIP_UPDATE_SUBMODULES,
        ]
        if self.docker:
            parts.append(_FLAG_DOCKER)
        if self.proxmox:
            parts.append(_FLAG_PROXMOX)
        parts.extend(self._flags)
        return " ".join(parts)

    @property
    def python3_infra(self) -> str:
        parts: list[str] = ["python3", "-m", "infra.install", FLAG_SKIP_PUBLIC]
        parts.extend(self._flags)
        return " ".join(parts)

    @property
    def _flags(self) -> list[str]:
        parts: list[str] = []
        if self.ib_gateway_docker:
            parts.append(FLAG_IB_GATEWAY_DOCKER)
        if self.gitlab:
            parts.append(FLAG_GITLAB)
        if self.gitlab_runner:
            parts.append(FLAG_GITLAB_RUNNER)
        if self.postgres:
            parts.append(FLAG_POSTGRES)
        if self.pypi:
            parts.append(FLAG_PYPI)
        if self.redis:
            parts.append(FLAG_REDIS)
        return parts


# main


def _main() -> None:
    basicConfig(
        format="{asctime} | {module}:{funcName}:{lineno} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
        level="INFO",
    )
    _LOGGER.info("'public' version: 0.4.121")
    settings = _Settings.parse()
    if not settings.post:
        _initial_install(settings)
    else:
        _post_install(settings)


def _initial_install(settings: _Settings, /) -> None:
    ###########################################################################
    # this installer may only contain standard library imports
    ###########################################################################
    _LOGGER.info("Initial installation...")
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir, "public")
        _clone_repo("https://github.com/queensberry-research/public.git", target)
        _run_command(settings.python3_public, env={"PYTHONPATH": "src"}, cwd=target)


def _post_install(settings: _Settings, /) -> None:
    ###########################################################################
    # this installer may only contain standard library & `public` imports
    ###########################################################################
    from .constants import HOME_INFRA
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
        install_yq,
        setup_bashrc,
        setup_ssh,
        setup_ssh_keys,
        setup_sshd,
    )
    from .storage import STORAGE_CONFIG
    from .utilities import (
        cp_named_temporary,
        full_path,
        log_installer_version,
        run_commands,
        update_submodules,
    )

    _LOGGER.info("Post installation...")
    log_installer_version()
    configs, subnet = _get_configs(), _get_subnet()
    if not settings.skip_update_submodules:
        update_submodules()
    if settings.proxmox or _is_proxmox():
        _setup_proxmox_sources()
        _setup_resolv_conf()
        _setup_subnet_env_var()
    add_to_known_hosts()
    setup_bashrc(bashrc=cp_named_temporary(configs / ".bashrc", skip_log=True))
    setup_ssh(
        symlinks=[
            (
                cp_named_temporary(configs / "github-infra-mirror", skip_log=True),
                "github-infra-mirror",
            )
        ],
        templates=[
            (configs / "gitlab-full", {"subnet": subnet}),
            (configs / "gitlab-infra", {"subnet": subnet}),
        ],
    )
    _setup_ssh_deploy_key()
    setup_ssh_keys(
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/ssh/keys.txt"
    )
    setup_sshd(permit_root_login=True)
    install_age()
    install_curl()
    install_direnv(direnv_toml=cp_named_temporary(configs / "direnv.toml"))
    install_fd()
    install_fzf()
    install_jq()
    install_just()
    neovim = full_path(TemporaryDirectory(delete=False).name, "neovim")
    _ = copytree(_get_repo_root() / "neovim", neovim)
    install_neovim(nvim_dir=neovim)
    install_ripgrep()
    install_rsync()
    install_starship(starship_toml=cp_named_temporary(configs / "starship.toml"))
    install_tmux(
        tmux_conf_oh_my_tmux=cp_named_temporary(configs / ".tmux.conf"),
        tmux_conf_local=cp_named_temporary(configs / "tmux.conf.local"),
    )
    install_vim()
    install_uv()  # after curl
    install_bottom()  # after curl, jq
    install_delta()  # after curl, jq
    if settings.proxmox or _is_proxmox():
        install_sops(  # after curl, jq
            age_secret_key=STORAGE_CONFIG.nfs.secrets / "age/secret-key.txt"
        )
    else:
        install_sops()
    install_yq()  # after curl, jq
    if settings.docker:
        install_docker()
    _clone_infra_mirror()
    run_commands(settings.python3_infra, cwd=HOME_INFRA)
    _LOGGER.info("Finished post installation")


# utilities - standard library


def _clone_repo(url: str, target: _PathLike, /) -> None:
    ###########################################################################
    # this function may only contain standard library imports
    ###########################################################################
    if not _have_command("git"):
        _LOGGER.info("Installing 'git'...")
        _run_command("apt -y update && apt install -y git")
    target = Path(target)
    if not target.exists():
        _LOGGER.info("Cloning %r to %r...", url, str(target))
        _run_command(f"git clone --recurse-submodules {url} {target}")


def _have_command(cmd: str, /) -> bool:
    ###########################################################################
    # this function may only contain standard library imports
    ###########################################################################
    return which(cmd) is not None


def _run_command(
    cmd: str, /, *, env: Mapping[str, str] | None = None, cwd: _PathLike | None = None
) -> None:
    ###########################################################################
    # this function may only contain standard library imports
    ###########################################################################
    desc = f"Running {cmd!r}"
    if env is None:
        env_use = None
    else:
        env_use = {**environ, **env}
        desc = f"{desc} [env={env}]"
    if cwd is not None:
        desc = f"{desc} [cwd={cwd}]"
    _LOGGER.info("%s...", desc)
    _ = check_call(cmd, executable=which("bash"), shell=True, cwd=cwd, env=env_use)


# utilities - standard library & public


def _get_configs() -> Path:
    return _get_repo_root() / "configs"


def _get_repo_root() -> Path:
    path_public = Path(__file__).parent
    path_src = path_public.parent
    return path_src.parent


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
    from .storage import STORAGE_CONFIG
    from .utilities import cp

    _LOGGER.info("Setting up Proxmox sources'...")
    cp(STORAGE_CONFIG.nfs.secrets / "deploy-key/infra", SSH / "infra")


def _setup_subnet_env_var() -> None:
    from .constants import HOME
    from .utilities import write_template

    path_from = _get_configs() / "subnet.sh"
    path_to = HOME / ".bashrc.d/subnet.sh"
    subnet = _get_subnet()
    write_template(path_from, path_to, subnet=subnet)


def _clone_infra_mirror() -> None:
    from .constants import HOME_INFRA
    from .utilities import git_pull, update_submodules

    if HOME_INFRA.exists():
        git_pull(cwd=HOME_INFRA)
        update_submodules(cwd=HOME_INFRA)
        return
    _clone_repo(
        "ssh://git@github-infra-mirror/queensberry-research/infra-mirror", HOME_INFRA
    )


# remote


def generate_curl_public_installer(
    *,
    post: bool = False,
    skip_update_submodules: bool = False,
    docker: bool = False,
    proxmox: bool = False,
    ib_gateway_docker: bool = False,
    gitlab: bool = False,
    gitlab_runner: bool = False,
    postgres: bool = False,
    pypi: bool = False,
    redis: bool = False,
) -> str:
    parts: list[str] = []
    if post:
        parts.append(_FLAG_POST)
    if skip_update_submodules:
        parts.append(_FLAG_SKIP_UPDATE_SUBMODULES)
    if docker:
        parts.append(_FLAG_DOCKER)
    if proxmox:
        parts.append(_FLAG_PROXMOX)
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
    cmd = " ".join(parts)
    return f"""{{ command -v curl >/dev/null 2>&1 || {{ apt -y update && apt -y install curl; }}; }}; curl -fsLS https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/public/install.py | python3 - {cmd}"""


__all__ = [
    "FLAG_GITLAB",
    "FLAG_GITLAB_RUNNER",
    "FLAG_IB_GATEWAY_DOCKER",
    "FLAG_POSTGRES",
    "FLAG_PYPI",
    "FLAG_PYPI",
    "FLAG_REDIS",
    "FLAG_SKIP_PUBLIC",
    "generate_curl_public_installer",
]


if __name__ == "__main__":
    _main()
