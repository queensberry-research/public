from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from shutil import copytree, which
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Literal, assert_never, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

###############################################################################
# NOTE: the top-level may only contain standard library imports
###############################################################################


type _Command = Literal["init", "post"]
type _PathLike = Path | str


_LOGGER = getLogger(__name__)
_INIT_CMD: _Command = "init"
_POST_CMD: _Command = "post"
_FLAG_AGE_SECRET_KEY = "--age-secret-key"  # noqa: S105
_FLAG_BRANCH = "--branch"
_FLAG_DEPLOY_KEY = "--deploy-key"
_FLAG_DOCKER = "--docker"
_FLAG_INFRA_CMD = "--infra-cmd"
_FLAG_INFRA_MIRROR = "--infra-mirror"
_FLAG_SKIP_UPDATE_SUBMODULES = "--skip-update-submodules"


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    command: _Command
    age_secret_key: Path | None
    branch: str | None
    deploy_key: Path | None
    docker: bool = False
    infra_cmd: str | None
    infra_mirror: bool = False
    skip_update_submodules: bool = False
    extra: list[str]

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        subparsers = parser.add_subparsers(dest="command", required=True)
        init_parser = subparsers.add_parser(_INIT_CMD, help="Initial installation")
        post_parser = subparsers.add_parser(_POST_CMD, help="Post installation")
        for p in [init_parser, post_parser]:
            _ = p.add_argument(
                _FLAG_AGE_SECRET_KEY,
                type=cls._to_path,
                help="Path to the `age` secret key",
                metavar="PATH",
            )
            _ = p.add_argument(
                _FLAG_BRANCH, type=str, help="Branch to use", metavar="BRANCH"
            )
            _ = p.add_argument(
                _FLAG_DEPLOY_KEY,
                type=cls._to_path,
                help="Path to the deploy key",
                metavar="PATH",
            )
            _ = p.add_argument(
                _FLAG_DOCKER, action="store_true", help="Install 'docker'"
            )
            _ = p.add_argument(
                _FLAG_INFRA_CMD,
                type=str,
                help="Command to run under the `infra` repo",
                metavar="COMMAND",
            )
            _ = p.add_argument(
                _FLAG_INFRA_MIRROR,
                action="store_true",
                help="Clone the `infra-mirror` repo",
            )
            _ = p.add_argument(
                _FLAG_SKIP_UPDATE_SUBMODULES,
                action="store_true",
                help="Skip updating of the submodules",
            )
        namespace, extra = parser.parse_known_args()
        match cast("_Command", namespace.command):
            case "init":
                namespace2, extra2 = init_parser.parse_known_args(extra)
            case "post":
                namespace2, extra2 = post_parser.parse_known_args(extra)
            case never:
                assert_never(never)
        kwargs = vars(namespace2) | vars(namespace)
        return _Settings(**kwargs, extra=extra2)

    @property
    def post_cmd(self) -> str:
        parts: list[str] = ["public.install", _POST_CMD]
        if self.age_secret_key is not None:
            parts.extend([_FLAG_AGE_SECRET_KEY, str(self.age_secret_key)])
        if self.branch is not None:
            parts.extend([_FLAG_BRANCH, str(self.branch)])
        if self.deploy_key is not None:
            parts.extend([_FLAG_DEPLOY_KEY, str(self.deploy_key)])
        if self.docker:
            parts.append(_FLAG_DOCKER)
        if self.infra_cmd is not None:
            parts.extend([_FLAG_INFRA_CMD, self.infra_cmd])
        if self.infra_mirror:
            parts.append(_FLAG_INFRA_MIRROR)
        if self.skip_update_submodules:
            parts.append(_FLAG_SKIP_UPDATE_SUBMODULES)
        return " ".join(parts)

    @classmethod
    def _to_path(cls, text: str, /) -> Path:
        return Path(text).expanduser()


# main


def _main() -> None:
    basicConfig(
        format="{asctime} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
        level="INFO",
    )
    _LOGGER.info("'public' version: 0.4.68")
    settings = _Settings.parse()
    match settings.command:
        case "init":
            _initial_install(settings)
        case "post":
            _post_install(settings)
        case never:
            assert_never(never)


def _initial_install(settings: _Settings, /) -> None:
    ###########################################################################
    # this installer may only contain standard library imports
    ###########################################################################
    _LOGGER.info("Initial installation...")
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir, "public")
        _clone_repo(
            "https://github.com/queensberry-research/public.git",
            target,
            branch=settings.branch,
        )
        _run_in_repo(settings.post_cmd, target, src=True)


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
        install_sops,
        install_starship,
        install_tmux,
        install_uv,
        install_vim,
        install_yq,
        setup_bashrc,
        setup_ssh_keys,
        setup_sshd,
    )
    from .utilities import (
        cp_named_temporary,
        full_path,
        log_installer_version,
        update_submodules,
    )

    _LOGGER.info("Post installation...")
    log_installer_version()
    path_public = Path(__file__).parent
    path_src = path_public.parent
    repo_root = path_src.parent
    path_configs = repo_root / "configs"
    if not settings.skip_update_submodules:
        update_submodules()
    add_to_known_hosts()
    setup_bashrc(bashrc=cp_named_temporary(path_configs / ".bashrc"))
    _setup_proxmox_sources()
    _setup_ssh_config(deploy_key=settings.deploy_key)
    setup_ssh_keys(
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/ssh/keys.txt"
    )
    setup_sshd(permit_root_login=True)
    install_age()
    install_curl()
    install_direnv()
    install_fd()
    install_fzf()
    install_jq()
    install_just()
    temp_neovim = TemporaryDirectory(delete=False)
    temp_neovim_inner = full_path(temp_neovim.name, "neovim")
    _ = copytree(repo_root / "neovim", temp_neovim_inner)
    install_neovim(nvim_dir=temp_neovim_inner)
    install_ripgrep()
    install_starship(starship_toml=cp_named_temporary(path_configs / "starship.toml"))
    install_tmux()
    install_vim()
    install_uv()  # after curl
    install_bottom()  # after curl, jq
    install_delta()  # after curl, jq
    install_sops(age_secret_key=settings.age_secret_key)  # after curl, jq
    install_yq()  # after curl, jq
    if settings.docker:
        install_docker()
    if settings.infra_mirror:
        _setup_infra_mirror(deploy_key=settings.deploy_key, branch=settings.branch)
    if settings.infra_cmd is not None:
        _run_in_repo(settings.infra_cmd, HOME_INFRA)


# utilities


def _clone_repo(url: str, target: _PathLike, /, *, branch: str | None = None) -> None:
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
        if branch is not None:
            _run_command(f"git checkout {branch}", cwd=target)
    _run_command(
        f"[ -f ~/.bashrc ] && source ~/.bashrc; command -v direnv >/dev/null 2>&1 && [ -f {target}/.envrc ] && direnv allow {target}"
    )


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
    if env is not None:
        desc = f"{desc} [env={env}]"
    if cwd is not None:
        desc = f"{desc} [cwd={cwd}]"
    _LOGGER.info("%s...", desc)
    _ = check_call(cmd, executable=which("bash"), shell=True, cwd=cwd, env=env)


def _run_in_repo(cmd: str, target: _PathLike, /, *, src: bool = False) -> None:
    ###########################################################################
    # this utility may only contain standard library imports
    ###########################################################################
    full_cmd = f"python3 -m {cmd}"
    env = {**environ, "PYTHONPATH": "src"} if src else None
    _run_command(full_cmd, cwd=target, env=env)


def _setup_proxmox_sources() -> None:
    from .constants import ETC
    from .utilities import apt_update, rm

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


def _setup_infra_mirror(
    *, deploy_key: _PathLike | None = None, branch: str | None = None
) -> None:
    from .constants import HOME_INFRA
    from .lib import setup_ssh_config

    if HOME_INFRA.exists():
        return
    if deploy_key is None:
        msg = (
            f"{_FLAG_DEPLOY_KEY!r} must be given since {_FLAG_INFRA_MIRROR!r} was given"
        )
        raise RuntimeError(msg)
    setup_ssh_config(host="github-infra-mirror", identity_file=deploy_key)
    _clone_repo(
        "ssh://git@github-infra-mirror/queensberry-research/infra-mirror",
        HOME_INFRA,
        branch=branch,
    )


def _setup_ssh_config(*, deploy_key: _PathLike | None = None) -> None:
    from .lib import setup_ssh_config

    if deploy_key is not None:
        setup_ssh_config(host="github-infra-mirror", identity_file=deploy_key)


# remote


def generate_curl_public_installer(
    *,
    age_secret_key: _PathLike | None = None,
    branch: str | None = None,
    deploy_key: _PathLike | None = None,
    docker: bool = False,
    infra_cmd: str | None = None,
    infra_mirror: bool = False,
    skip_update_submodules: bool = False,
) -> str:
    parts: list[str] = []
    if age_secret_key is not None:
        parts.extend([_FLAG_AGE_SECRET_KEY, str(age_secret_key)])
    if branch is not None:
        parts.extend([_FLAG_BRANCH, str(branch)])
    if deploy_key is not None:
        parts.extend([_FLAG_DEPLOY_KEY, str(deploy_key)])
    if docker:
        parts.append(_FLAG_DOCKER)
    if infra_cmd is not None:
        parts.extend([_FLAG_INFRA_CMD, infra_cmd])
    if infra_mirror:
        parts.append(_FLAG_INFRA_MIRROR)
    if skip_update_submodules:
        parts.append(_FLAG_SKIP_UPDATE_SUBMODULES)
    cmd = " ".join(parts)
    return f"""rm -f /etc/apt/sources.list.d{{ceph,pve-enterprise}}.sources; command -v curl >/dev/null 2>&1 || {{ apt -y update; ; }}; curl -fsLS https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/public/install.py | python3 - {_INIT_CMD} {cmd}"""


__all__ = ["generate_curl_public_installer"]


if __name__ == "__main__":
    _main()
