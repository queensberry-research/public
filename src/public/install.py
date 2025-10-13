from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from shutil import which
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import ClassVar, Literal, assert_never, cast
from urllib.parse import urlparse

###############################################################################
# NOTE: the top-level may only contain standard library imports
###############################################################################

type _Command = Literal["init", "post"]
type PathLike = Path | str

_LOGGER = getLogger(__name__)

# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    command: _Command
    age_secret_key: Path | None
    bashrc: Path | None
    deploy_key: Path | None
    direnv_toml: Path | None
    dev: bool = False
    docker: bool = False
    infra_cmd: bool = False
    nvim_dir: Path | None
    skip_update_submodules: bool = False
    starship_toml: Path | None
    extra: list[str]

    _flag_age_secret_key: ClassVar[str] = "--age-secret-key"  # noqa: S105
    _flag_bashrc: ClassVar[str] = "--bashrc"
    _flag_deploy_key: ClassVar[str] = "--deploy-key"
    _flag_direnv_toml: ClassVar[str] = "--direnv-toml"
    _flag_dev: ClassVar[str] = "--dev"
    _flag_docker: ClassVar[str] = "--docker"
    _flag_infra_cmd: ClassVar[str] = "--infra-cmd"
    _flag_nvim_dir: ClassVar[str] = "--nvim-dir"
    _flag_skip_update_submodules: ClassVar[str] = "--skip-update-submodules"
    _flag_starship_toml: ClassVar[str] = "--starship-toml"

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        subparsers = parser.add_subparsers(dest="command", required=True)
        cmd: _Command = "init"
        init = subparsers.add_parser(cmd, help="Initial installation")
        cmd: _Command = "post"
        post = subparsers.add_parser(cmd, help="Post installation")
        for p in [init, post]:
            _ = p.add_argument(
                cls._flag_age_secret_key,
                type=cls._to_path,
                help="Path to the `age` secret key",
                metavar="PATH",
            )
            _ = p.add_argument(
                cls._flag_bashrc,
                type=cls._to_path,
                help="Path to the `.bashrc`",
                metavar="PATH",
            )
            _ = p.add_argument(
                cls._flag_deploy_key,
                type=cls._to_path,
                help="Path to the deploy key",
                metavar="PATH",
            )
            _ = p.add_argument(
                cls._flag_direnv_toml,
                type=cls._to_path,
                help="Path to the `direnv.toml`",
                metavar="PATH",
            )
            _ = p.add_argument(
                cls._flag_dev,
                action="store_true",
                help="Install development dependencies",
            )
            _ = p.add_argument(
                cls._flag_docker, action="store_true", help="Install 'docker'"
            )
            _ = p.add_argument(
                cls._flag_nvim_dir,
                type=cls._to_path,
                help="Path to the `nvim` directory",
                metavar="PATH",
            )
            _ = p.add_argument(
                cls._flag_skip_update_submodules,
                action="store_true",
                help="Skip updating of the submodules",
            )
            _ = p.add_argument(
                cls._flag_starship_toml,
                type=cls._to_path,
                help="Path to the `starship.toml`",
                metavar="PATH",
            )
        namespace, extra = parser.parse_known_args()
        match cast("_Command", namespace.command):
            case "init":
                namespace2, extra2 = init.parse_known_args(extra)
            case "post":
                namespace2, extra2 = post.parse_known_args(extra)
            case never:
                assert_never(never)

        kwargs = vars(namespace2) | vars(namespace)
        return _Settings(**kwargs, extra=extra2)

    @property
    def post_cmd(self) -> str:
        parts: list[str] = ["public.install"]
        cmd: _Command = "post"
        parts.append(cmd)
        if self.age_secret_key is not None:
            parts.extend([self._flag_age_secret_key, str(self.age_secret_key)])
        if self.bashrc is not None:
            parts.extend([self._flag_bashrc, str(self.bashrc)])
        if self.deploy_key is not None:
            parts.extend([self._flag_deploy_key, str(self.deploy_key)])
        if self.direnv_toml is not None:
            parts.extend([self._flag_direnv_toml, str(self.direnv_toml)])
        if self.dev:
            parts.append(self._flag_dev)
        if self.docker:
            parts.append(self._flag_docker)
        if self.skip_update_submodules:
            parts.append(self._flag_skip_update_submodules)
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
    _ensure_cloned_and_run(
        "https://github.com/queensberry-research/public.git",
        settings.post_cmd,
        src=True,
    )


def _post_install(settings: _Settings, /) -> None:
    ###########################################################################
    # this installer may only contain standard library & `public` imports
    ###########################################################################
    from public.constants import HOME
    from public.lib import (
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
    from public.utilities import update_submodules

    _LOGGER.info("Post installation...")
    if not settings.skip_update_submodules:
        update_submodules()
    setup_bashrc(bashrc=settings.bashrc)
    _setup_proxmox_sources()
    _setup_ssh_config(deploy_key=settings.deploy_key)
    setup_ssh_keys(
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/ssh/keys.txt"
    )
    setup_sshd(permit_root_login=True)
    install_age()
    install_curl()
    install_direnv(direnv_toml=settings.direnv_toml)
    install_jq()
    install_uv()  # after curl
    install_yq()  # after curl, jq
    install_sops(age_secret_key=settings.age_secret_key)  # after curl, jq
    if settings.docker:
        install_docker()
    if settings.dev:
        install_bottom()  # after curl, jq
        install_delta()
        install_fd()
        install_fzf()
        install_just()
        install_neovim(nvim_dir=settings.nvim_dir)
        install_ripgrep()
        install_starship(starship_toml=settings.starship_toml)
        install_tmux()
        install_vim()
    if (settings.deploy_key is not None) and settings.infra_cmd:
        _ensure_cloned_and_run(
            "https://github.com/queensberry-research/infra-mirror.git",
            f"{settings.infra_cmd} {settings.extra}",
            target=HOME / "infra",
        )


# utilities


def _clone_repo(url: str, target: PathLike, /) -> None:
    _LOGGER.info("Cloning %r...", url)
    _ = check_call(f"git clone {url} {target}", shell=True)


def _clone_repo_and_run_core(
    url: str, target: PathLike, cmd: str, /, *, src: bool = False
) -> None:
    _clone_repo(url, target)
    _run_in_repo(cmd, target, src=src)


def _ensure_cloned_and_run(
    url: str, cmd: str, /, *, target: PathLike | None = None, src: bool = False
) -> None:
    if which("git") is None:
        _LOGGER.info("Installing 'git'...")
        _ = check_call("apt -y update && apt install -y git", shell=True)
    if target is None:
        with TemporaryDirectory() as temp_dir:
            repo_name = Path(urlparse(url).path).stem
            target = Path(temp_dir, repo_name)
            _clone_repo_and_run_core(url, target, cmd, src=src)
    else:
        target = Path(target)
        if target.exists():
            _run_in_repo(cmd, target, src=src)
        else:
            _clone_repo_and_run_core(url, target, cmd, src=src)


def _run_in_repo(cmd: str, target: PathLike, /, *, src: bool = False) -> None:
    full_cmd = f"python3 -m {cmd}"
    target = Path(target)
    _LOGGER.info("Running %r in %r...", full_cmd, str(target))
    env = dict(environ)
    if src:
        env["PYTHONPATH"] = "src"
    _ = check_call(full_cmd, shell=True, cwd=target, env=env)


def _setup_proxmox_sources() -> None:
    from public.more_constants import ETC
    from public.utilities import apt_update, rm

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


def _setup_ssh_config(*, deploy_key: PathLike | None = None) -> None:
    from public.lib import setup_ssh_config

    if deploy_key is not None:
        setup_ssh_config(host="github-infra-mirror", identity_file=deploy_key)


if __name__ == "__main__":
    _main()
