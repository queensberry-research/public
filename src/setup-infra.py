#!/usr/bin/env python3.11
from __future__ import annotations

import tarfile
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from logging import basicConfig, getLogger
from os import environ, geteuid
from pathlib import Path
from shutil import copyfile, copytree, rmtree, which
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, assert_never
from urllib.parse import urlparse
from urllib.request import urlopen

if TYPE_CHECKING:
    from collections.abc import Iterator


_LOGGER = getLogger(__name__)
_AGE_VERSION = "1.2.1"
_BOTTOM_VERSION = "0.11.1"
_DELTA_VERSION = "0.18.2"
_DIRENV_VERSION = "2.37.1"
_JUST_VERSION = "1.42.4"
_NEOVIM_VERSION = "0.11.4"
_STARSHIP_VERSION = "1.23.0"
_UV_VERSION = "0.8.22"
basicConfig(
    format="{asctime} | {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO"
)


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True)
class _Settings:
    # age
    age: bool = False
    age_force: bool = False
    age_version: str = _AGE_VERSION
    # bottom
    bottom: bool = False
    bottom_force: bool = False
    bottom_version: str = _BOTTOM_VERSION
    # curl
    curl: bool = False
    curl_force: bool = False
    # delta
    delta: bool = False
    delta_force: bool = False
    delta_version: str = _DELTA_VERSION
    # direnv
    direnv: bool = False
    direnv_force: bool = False
    direnv_version: str = _DIRENV_VERSION
    # docker
    docker: bool = False
    docker_force: bool = False
    # git
    git: bool = False
    git_force: bool = False
    # just
    just: bool = False
    just_force: bool = False
    just_version: str = _JUST_VERSION
    # lazyvim
    lazyvim: bool = False
    lazyvim_force: bool = False
    # neovim
    neovim: bool = False
    neovim_force: bool = False
    neovim_version: str = _NEOVIM_VERSION
    # proxmox
    proxmox_apt: bool = False
    # SSH keys
    ssh_keys: bool = False
    ssh_keys_mode: SSHKeysMode
    # starship
    starship: bool = False
    starship_force: bool = False
    starship_version: str = _STARSHIP_VERSION
    # uv
    uv: bool = False
    uv_force: bool = False
    uv_version: str = _UV_VERSION
    # vim
    vim: bool = False
    vim_force: bool = False

    @property
    def git_use(self) -> bool:
        return self.git or self.lazyvim

    @property
    def neovim_use(self) -> bool:
        return self.neovim or self.lazyvim

    @property
    def proxmox_apt_use(self) -> bool:
        return self.proxmox_apt or self.git_use or self.vim

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        # age
        parser.add_argument("-a", "--age", action="store_true", help="Install 'age'")
        parser.add_argument(
            "--age-force", action="store_true", help="Force install 'age'"
        )
        parser.add_argument(
            "--age-version",
            default=_AGE_VERSION,
            type=str,
            help="'age' version",
            metavar="STR",
        )
        # bottom
        parser.add_argument(
            "-b", "--bottom", action="store_true", help="Install 'bottom'"
        )
        parser.add_argument(
            "--bottom-force", action="store_true", help="Force install 'bottom'"
        )
        parser.add_argument(
            "--bottom-version",
            default=_BOTTOM_VERSION,
            type=str,
            help="'bottom' version",
            metavar="STR",
        )
        # curl
        parser.add_argument("-c", "--curl", action="store_true", help="Install 'curl'")
        parser.add_argument(
            "--curl-force", action="store_true", help="Force install 'curl'"
        )
        # delta
        parser.add_argument(
            "-de", "--delta", action="store_true", help="Install 'delta'"
        )
        parser.add_argument(
            "--delta-force", action="store_true", help="Force install 'delta'"
        )
        parser.add_argument(
            "--delta-version",
            default=_DELTA_VERSION,
            type=str,
            help="'delta' version",
            metavar="STR",
        )
        # direnv
        parser.add_argument(
            "-di", "--direnv", action="store_true", help="Install 'direnv'"
        )
        parser.add_argument(
            "--direnv-force", action="store_true", help="Force install 'direnv'"
        )
        parser.add_argument(
            "--direnv-version",
            default=_DIRENV_VERSION,
            type=str,
            help="'direnv' version",
            metavar="STR",
        )
        # docker
        parser.add_argument(
            "-do", "--docker", action="store_true", help="Install 'docker'"
        )
        parser.add_argument(
            "--docker-force", action="store_true", help="Force install 'docker'"
        )
        # git
        parser.add_argument("-g", "--git", action="store_true", help="Install 'git'")
        parser.add_argument(
            "--git-force", action="store_true", help="Force install 'git'"
        )
        # just
        parser.add_argument("-j", "--just", action="store_true", help="Install 'just'")
        parser.add_argument(
            "--just-force", action="store_true", help="Force install 'just'"
        )
        parser.add_argument(
            "--just-version",
            default=_JUST_VERSION,
            type=str,
            help="'just' version",
            metavar="STR",
        )
        # lazyvim
        parser.add_argument(
            "-l", "--lazyvim", action="store_true", help="Install 'lazyvim'"
        )
        parser.add_argument(
            "--lazyvim-force", action="store_true", help="Force install 'lazyvim'"
        )
        # neovim
        parser.add_argument(
            "-n", "--neovim", action="store_true", help="Install 'neovim'"
        )
        parser.add_argument(
            "--neovim-force", action="store_true", help="Force install 'neovim'"
        )
        parser.add_argument(
            "--neovim-version",
            default=_NEOVIM_VERSION,
            type=str,
            help="'neovim' version",
            metavar="STR",
        )
        # proxmox
        parser.add_argument(
            "-pa", "--proxmox-apt", action="store_true", help="Setup proxmox apt"
        )
        # SSH keys
        parser.add_argument(
            "-sk", "--ssh-keys", action="store_true", help="Add SSH keys"
        )
        parser.add_argument(
            "--ssh-keys-mode",
            type=SSHKeysMode,
            choices=list(SSHKeysMode),
            default=SSHKeysMode.overwrite,
            help="How to handle SSH keys",
        )
        # starship
        parser.add_argument(
            "-st", "--starship", action="store_true", help="Install 'starship'"
        )
        parser.add_argument(
            "--starship-force", action="store_true", help="Force install 'starship'"
        )
        parser.add_argument(
            "--starship-version",
            default=_STARSHIP_VERSION,
            type=str,
            help="'starship' version",
            metavar="STR",
        )
        # uv
        parser.add_argument("-u", "--uv", action="store_true", help="Install 'uv'")
        parser.add_argument(
            "--uv-force", action="store_true", help="Force install 'uv'"
        )
        parser.add_argument(
            "--uv-version",
            default=_UV_VERSION,
            type=str,
            help="'uv' version",
            metavar="STR",
        )
        # vim
        parser.add_argument("-v", "--vim", action="store_true", help="Install 'vim'")
        parser.add_argument(
            "--vim-force", action="store_true", help="Force install 'vim'"
        )
        return _Settings(**vars(parser.parse_args()))


class SSHKeysMode(StrEnum):
    overwrite = "overwrite"
    append = "append"


class Shell(StrEnum):
    bash = "bash"
    zsh = "zsh"

    @classmethod
    def get(cls) -> Shell:
        match Path(environ["SHELL"]).name:
            case "bash":
                return Shell.bash
            case "zsh":
                return Shell.zsh
            case shell:
                msg = f"Invalid shell: {shell!r}"
                raise ValueError(msg)

    @property
    def path_rc(self) -> Path:
        return Path.home().joinpath(f".{self.name}rc")


# library - main


def setup_age(*, force: bool = False, version: str = _AGE_VERSION) -> None:
    if _has_command("age") and not force:
        _LOGGER.info("'age' is already set up")
        return
    _LOGGER.info("Setting up 'age' %s...", version)
    url = _github_url(
        "FiloSottile", "age", f"v{version}", f"age-v{version}-linux-amd64.tar.gz"
    )
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        (dir_from,) = temp_dir.iterdir()
        for name in ["age", "age-keygen"]:
            path_from = dir_from.joinpath(name)
            path_to = _local_bin().joinpath(name)
            _copyfile_logged(path_from, path_to, executable=True)


def setup_bottom(*, force: bool = False, version: str = _BOTTOM_VERSION) -> None:
    if _has_command("btm") and not force:
        _LOGGER.info("'bottom' is already set up")
        return
    _LOGGER.info("Setting up 'bottom' %s...", version)
    url = _github_url(
        "ClementTsang", "bottom", version, f"bottom_{version}-1_amd64.deb"
    )
    with _yield_download(url) as temp_file:
        cmd = ["dpkg", "-i", str(temp_file)]
        check_call(_prepend_sudo_if_not_root(cmd))


def setup_curl(*, force: bool = False) -> None:
    _setup_via_apt("curl", force=force)


def setup_delta(*, force: bool = False, version: str = _DELTA_VERSION) -> None:
    if _has_command("delta") and not force:
        _LOGGER.info("'delta' is already set up")
        return
    _LOGGER.info("Setting up 'delta' %s...", version)
    url = _github_url(
        "dandavison",
        "delta",
        version,
        f"delta-{version}-x86_64-unknown-linux-gnu.tar.gz",
    )
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        (dir_from,) = temp_dir.iterdir()
        path_from = dir_from.joinpath("delta")
        path_to = _local_bin().joinpath("delta")
        _copyfile_logged(path_from, path_to, executable=True)


def setup_direnv(*, force: bool = False, version: str = _DIRENV_VERSION) -> None:
    if _has_command("direnv") and not force:
        _LOGGER.info("'direnv' is already set up")
        return
    _LOGGER.info("Setting up 'direnv'...")
    url = _github_url("direnv", "direnv", f"v{version}", "direnv.linux-amd64")
    with _yield_download(url) as temp_file:
        path_to = _local_bin().joinpath("direnv")
        _copyfile_logged(temp_file, path_to, executable=True)
    _append_to_rc(f"""eval "$(direnv hook {Shell.get().name})" """)


def setup_docker(*, force: bool = False) -> None:
    if _has_command("docker") and not force:
        _LOGGER.info("'docker' is already set up")
        return
    _LOGGER.info("Setting up 'docker'...")
    for pkg in [
        "docker.io",
        "docker-doc",
        "docker-compose",
        "podman-docker",
        "containerd",
        "runc",
    ]:
        check_call(["apt-get", "remove", pkg])
    for cmd in [
        "apt-get update",
        "apt-get -y install ca-certificates curl",
        "install -m 0755 -d /etc/apt/keyrings",
        "curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc",
        "chmod a+r /etc/apt/keyrings/docker.asc",
        """echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null""",
        "apt-get update",
        "apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        "usermod -aG docker $USER",
    ]:
        check_call(cmd, shell=True)


def setup_git(*, force: bool = False) -> None:
    _setup_via_apt("git", force=force)


def setup_just(*, force: bool = False, version: str = _JUST_VERSION) -> None:
    if _has_command("just") and not force:
        _LOGGER.info("'just' is already set up")
        return
    _LOGGER.info("Setting up 'just'...")
    url = _github_url(
        "casey", "just", version, f"just-{version}-x86_64-unknown-linux-musl.tar.gz"
    )
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        path_from = temp_dir.joinpath("just")
        path_to = _local_bin().joinpath("just")
        _copyfile_logged(path_from, path_to, executable=True)


def setup_lazyvim(*, force: bool = False) -> None:
    home = Path.home()
    nvim = home.joinpath(".config", "nvim")
    lua = nvim.joinpath("lua")
    lazy = lua.joinpath("config", "lazy.lua")
    if lazy.exists() and not force:
        _LOGGER.info("'lazyvim' is already set up")
        return
    _LOGGER.info("Setting up 'lazyvim'...")
    for tail in [
        Path(".config", "nvim"),
        Path(".local", "share"),
        Path(".local", "state"),
        Path(".cache", "nvim"),
    ]:
        _unlink_logged(home.joinpath(tail))
    check_call(["git", "clone", "https://github.com/LazyVim/starter", str(nvim)])
    path = lua.joinpath("plugins", "auto-save.lua")
    _unlink_logged(path)
    _LOGGER.info("Writing %r...", str(path))
    path.write_text("""
return { "pocco81/auto-save.nvim }
""")


def setup_neovim(*, force: bool = False, version: str = _NEOVIM_VERSION) -> None:
    if _has_command("nvim") and not force:
        _LOGGER.info("'neovim' is already set up")
        return
    _LOGGER.info("Setting up 'neovim'...")
    stem = "nvim-linux-x86_64"
    url = _github_url("neovim", "neovim", f"v{version}", f"{stem}.tar.gz")
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        (path_from,) = temp_dir.iterdir()
        path_to = _local_bin().joinpath("neovim", stem)
        _copytree_logged(path_from, path_to)
    path_from = _local_bin().joinpath("nvim")
    _unlink_logged(path_from)
    path_to = _local_bin().joinpath("neovim", stem, "bin", "nvim")
    path_from.symlink_to(path_to)
    _append_to_rc("""alias n='nvim'""")


def setup_proxmox_apt() -> None:
    any_removed = any(
        _setup_proxmox_apt_remove(name) for name in ["ceph", "pve-enterprise"]
    )
    if any_removed:
        _update_apt()


def _setup_proxmox_apt_remove(name: str, /) -> bool:
    path = Path("/etc", "apt", "sources.list.d", f"{name}.sources")
    if path.exists():
        _unlink_logged(path)
        return True
    _LOGGER.info("%r is already removed", str(path))
    return False


def setup_rc() -> None:
    _LOGGER.info("Setting up %r...", Shell.get().path_rc.name)
    for line in [
        """alias ~='cd "${HOME}"'""",
        """alias ..='cd ..'""",
        """alias ...='cd ../..'""",
        """alias ....='cd ../../..'""",
        """alias bashrc='$EDITOR "${HOME}/.bashrc"'""",
        """alias gb='git branch --all --verbose'""",
        """alias gc='git checkout'""",
        """alias gd='git diff'""",
        """alias gf='git fetch --all --prune --prune-tags --recurse-submodules=yes --tags'""",
        """alias gl='git log --oneline'""",
        """alias gp='git pull --all --ff-only --prune --tags'""",
        """alias gpw='watch -n2 "git pull --all --ff-only --prune --tags || git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)"'""",
        """alias gs='git status'""",
        """alias l='ls -al --color=auto'""",
        """alias zshrc='$EDITOR "${HOME}/.zshrc"'""",
    ]:
        _append_to_rc(line)
    _append_to_rc("""export EDITOR=$(command -v nvim || command -v vim || echo vi)""")
    _append_to_rc('''export PATH="${HOME}/.local/bin${PATH:+:${PATH}}"''')
    match Shell.get():
        case Shell.bash:
            line = "set -o vi"
        case Shell.zsh:
            line = "bindkey -v"
        case never:
            assert_never(never)
    _append_to_rc(line)


def setup_ssh_keys(*, mode: SSHKeysMode) -> None:
    _LOGGER.info("Setting up SSH keys...")
    url = "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/ssh-keys.txt"
    path = Path.home().joinpath(".ssh", "authorized_keys")
    with _yield_download(url) as temp_file:
        match mode:
            case SSHKeysMode.overwrite:
                _copyfile_logged(temp_file, path)
            case SSHKeysMode.append:
                for key in temp_file.read_text().splitlines():
                    _append_to_file(key, path)
            case never:
                assert_never(never)
    path.chmod(S_IRUSR | S_IWUSR)


def setup_starship(*, force: bool = False, version: str = _STARSHIP_VERSION) -> None:
    if _has_command("starship") and not force:
        _LOGGER.info("'starship' is already set up")
        return
    _LOGGER.info("Setting up 'starship'...")
    url = _github_url(
        "starship",
        "starship",
        f"v{version}",
        "starship-x86_64-unknown-linux-gnu.tar.gz",
    )
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        (path_from,) = temp_dir.iterdir()
        path_to = _local_bin().joinpath("starship")
        _copyfile_logged(path_from, path_to, executable=True)
    _append_to_rc(f"""eval "$(starship init {Shell.get().name})" """)


def setup_uv(*, force: bool = False, version: str = _UV_VERSION) -> None:
    if _has_command("uv") and not force:
        _LOGGER.info("'uv' is already set up")
        return
    url = _github_url("astral-sh", "uv", version, "uv-x86_64-unknown-linux-gnu.tar.gz")
    with (
        _yield_download(url) as temp_file,
        _yield_tar_gz_contents(temp_file) as temp_dir,
    ):
        (dir_from,) = temp_dir.iterdir()
        for name in ["uv", "uvx"]:
            path_from = dir_from.joinpath(name)
            path_to = _local_bin().joinpath(name)
            _copyfile_logged(path_from, path_to, executable=True)


def setup_vim(*, force: bool = False) -> None:
    _setup_via_apt("vim", force=force)


# library - utilities


def _append_to_file(line: str, path: Path, /) -> None:
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        _LOGGER.info("Writing %r to %r...", line, str(path))
        with path.open(mode="w") as fh:
            fh.write(f"{line}\n")
    else:
        if any(line_i == line for line_i in lines):
            _LOGGER.info("%r already in %r", line, str(path))
        else:
            _LOGGER.info("Appending %r to %r...", line, str(path))
            with path.open(mode="a") as fh:
                fh.write(f"{line}\n")


def _append_to_rc(line: str, /) -> None:
    return _append_to_file(line, Shell.get().path_rc)


def _copyfile_logged(
    path_from: Path, path_to: Path, /, *, executable: bool = False
) -> None:
    _unlink_logged(path_to)
    _LOGGER.info("Copying %r -> %r...", str(path_from), str(path_to))
    path_to.parent.mkdir(parents=True, exist_ok=True)
    copyfile(path_from, path_to)
    if executable:
        _set_executable(path_to)


def _copytree_logged(path_from: Path, path_to: Path, /) -> None:
    if path_to.exists():
        _LOGGER.info("Removing %r...", str(path_to))
        rmtree(path_to)
    path_to.parent.mkdir(parents=True, exist_ok=True)
    _LOGGER.info("Copying %r -> %r...", str(path_from), str(path_to))
    copytree(path_from, path_to)


def _github_url(owner: str, repo: str, version: str, filename: str, /) -> str:
    return f"https://github.com/{owner}/{repo}/releases/download/{version}/{filename}"


def _has_command(cmd: str, /) -> bool:
    return which(cmd) is not None


def _local_bin() -> Path:
    return Path.home().joinpath(".local", "bin")


def _prepend_sudo_if_not_root(cmd: list[str], /) -> list[str]:
    return cmd if _is_root() else ["sudo", *cmd]


def _is_root() -> bool:
    return geteuid() == 0


def _unlink_logged(path: Path, /) -> None:
    if path.exists():
        _LOGGER.info("Removing %r...", str(path))
        path.unlink(missing_ok=True)


def _set_executable(path: Path, /) -> None:
    mode = path.stat().st_mode
    if mode & S_IXUSR:
        _LOGGER.info("%r is already executable", str(path))
        return
    _LOGGER.info("Making %r executable...", str(path))
    path.chmod(mode | S_IXUSR)


def _setup_via_apt(cmd: str, /, *, force: bool = False) -> None:
    if _has_command(cmd) and not force:
        _LOGGER.info("%r is already set up", cmd)
        return
    _LOGGER.info("Setting up %r...", str(cmd))
    _update_apt()
    check_call(_prepend_sudo_if_not_root(["apt", "install", "-y", cmd]))


def _update_apt() -> None:
    _LOGGER.info("Updating 'apt'...")
    cmd = ["apt", "update"]
    check_call(_prepend_sudo_if_not_root(cmd))


@contextmanager
def _yield_download(url: str, /) -> Iterator[Path]:
    filename = Path(urlparse(url).path).name
    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir, filename)
        with urlopen(url) as response, temp_file.open(mode="wb") as fh:
            fh.write(response.read())
        yield temp_file


@contextmanager
def _yield_tar_gz_contents(path: Path, /) -> Iterator[Path]:
    with tarfile.open(path, mode="r:gz") as tf, TemporaryDirectory() as temp_dir:
        _ = tf.extractall(path=temp_dir)
        yield Path(temp_dir)


__all__ = [
    "setup_age",
    "setup_bottom",
    "setup_curl",
    "setup_direnv",
    "setup_git",
    "setup_just",
    "setup_lazyvim",
    "setup_neovim",
    "setup_proxmox_apt",
    "setup_rc",
    "setup_ssh_keys",
    "setup_starship",
    "setup_uv",
    "setup_vim",
]


# script


def main() -> None:
    settings = _Settings.parse()
    _LOGGER.info("Setting up infra...")
    setup_rc()
    if settings.proxmox_apt_use:
        setup_proxmox_apt()
    if settings.git_use:  # after proxmox_apt
        setup_git(force=settings.git_force)
    if settings.vim:  # after proxmox_apt
        setup_vim(force=settings.vim_force)
    if settings.neovim_use:
        setup_neovim(force=settings.neovim_force, version=settings.neovim_version)
    if settings.lazyvim:  # after neovim
        setup_lazyvim(force=settings.lazyvim_force)
    if settings.age:
        setup_age(force=settings.age_force, version=settings.age_version)
    if settings.bottom:
        setup_bottom(force=settings.bottom_force, version=settings.bottom_version)
    if settings.curl:
        setup_curl(force=settings.curl_force)
    if settings.delta:
        setup_delta(force=settings.delta_force, version=settings.delta_version)
    if settings.direnv:
        setup_direnv(force=settings.direnv_force, version=settings.direnv_version)
    if settings.docker:
        setup_docker(force=settings.docker_force)
    if settings.just:
        setup_just(force=settings.just_force)
    if settings.ssh_keys:
        setup_ssh_keys(mode=settings.ssh_keys_mode)
    if settings.starship:
        setup_starship(force=settings.starship_force, version=settings.starship_version)
    if settings.uv:
        setup_uv(force=settings.uv_force, version=settings.uv_version)


if __name__ == "__main__":
    main()
