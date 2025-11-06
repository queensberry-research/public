from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from contextlib import contextmanager
from dataclasses import dataclass
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from shutil import which
from socket import gethostname
from string import Template
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING, ClassVar, assert_never
from urllib.request import urlopen

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


basicConfig(
    format=f"[{{asctime}} ❯ {gethostname()} ❯ {{module}}:{{funcName}}:{{lineno}}] {{message}}",  # noqa: RUF001
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level="INFO",
)
_LOGGER = getLogger(__name__)


# types


type _PathLike = Path | str


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class _Settings:
    # classvars
    default_non_root_username: ClassVar[str] = "nonroot"
    default_path_bin: ClassVar[Path] = Path("~/.local/bin")
    default_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master"
    )
    default_authorized_keys: ClassVar[str] = "$url/ssh/keys.txt"
    default_bashrc: ClassVar[str] = "$url/configs/.bashrc"
    default_direnv_toml: ClassVar[str] = "$url/configs/direnv.toml"
    default_git_config: ClassVar[str] = "$url/configs/git-config"
    default_sshd_config: ClassVar[str] = "$url/configs/sshd_config"
    default_starship_toml: ClassVar[str] = "$url/configs/starship.toml"

    # fields

    root_password: str | None = None
    non_root_username: str = default_non_root_username
    non_root_password: str | None = None
    path_local_bin: Path = default_path_bin
    url: str = default_url
    authorized_keys: str = default_authorized_keys
    bashrc: str = default_bashrc
    direnv_toml: str = default_direnv_toml
    git_config: str = default_git_config
    sshd_config: str = default_sshd_config
    starship_toml: str = default_starship_toml
    runtime: bool = False
    docker: bool = False

    @classmethod
    def parse(cls) -> _Settings:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument("--root-password", type=str, help="'root' password")
        _ = parser.add_argument(
            "--non-root-username",
            default=cls.default_non_root_username,
            type=str,
            help="Non-root username",
        )
        _ = parser.add_argument(
            "--non-root-password", type=str, help="Non-root password"
        )
        _ = parser.add_argument(
            "--path-local-bin",
            default=cls.default_path_bin,
            type=Path,
            help="Path to the local binaries",
        )
        _ = parser.add_argument(
            "--url", default=cls.default_url, type=str, help="Config repo URL"
        )
        _ = parser.add_argument(
            "--authorized-keys",
            default=cls.default_authorized_keys,
            type=str,
            help="'authorized_keys' file or URL",
        )
        _ = parser.add_argument(
            "--bashrc",
            default=cls.default_bashrc,
            type=str,
            help="'.bashrc' file or URL",
        )
        _ = parser.add_argument(
            "--direnv-toml",
            default=cls.default_direnv_toml,
            type=str,
            help="'direnv.toml' file or URL",
        )
        _ = parser.add_argument(
            "--git-config",
            default=cls.default_git_config,
            type=str,
            help="'git' config file or URL",
        )
        _ = parser.add_argument(
            "--sshd-config",
            default=cls.default_sshd_config,
            type=str,
            help="'sshd_config' file or URL",
        )
        _ = parser.add_argument(
            "--starship-toml",
            default=cls.default_starship_toml,
            type=str,
            help="'starship.toml' file or URL",
        )
        _ = parser.add_argument(
            "--runtime", action="store_true", help="Install runtime tools"
        )
        _ = parser.add_argument("--docker", action="store_true", help="Install Docker")
        return _Settings(**vars(parser.parse_args()))

    # installer

    def install(self) -> None:
        self._set_root_password()
        self._create_user()
        _apt_install("curl")
        self._setup_sshd_config()
        for non_root in [False, True]:
            self._setup_authorized_keys(non_root=non_root)
            self._setup_known_hosts(non_root=non_root)
            self._setup_bashrc(non_root=non_root)
            self._setup_git_config(non_root=non_root)
            self._install_starship(non_root=non_root)
        self._install_runtime_tools()

    def _set_root_password(self) -> None:
        if (password := self.root_password) is None:
            _LOGGER.info("Skipping the setting of 'root' password...")
            return
        _LOGGER.info("Setting 'root' password...")
        _ = self._run(f"echo 'root:{password}' | chpasswd")

    def _create_user(self) -> None:
        username = self.non_root_username
        try:
            _ = self._run(f"id -u {username}")
        except CalledProcessError:
            _LOGGER.info("Creating %r...", username)
            _ = self._run(
                f"useradd --create-home --shell /bin/bash {username}",
                f"usermod -aG sudo {username}",
            )
        else:
            _LOGGER.info("%r already exists", username)
        if (password := self.non_root_password) is None:
            _LOGGER.info("Skipping the setting of %r password...", username)
            return
        _LOGGER.info("Setting %r password...", username)
        _ = self._run(f"echo '{username}:{password}' | chpasswd")

    def _setup_sshd_config(self) -> None:
        self._copy_file_or_url(self._with_url(self.sshd_config), "/etc/ssh/sshd_config")

    def _setup_authorized_keys(self, *, non_root: bool = False) -> None:
        self._copy_file_or_url(
            self._with_url(self.authorized_keys),
            "~/.ssh/authorized_keys",
            non_root=non_root,
        )

    def _setup_known_hosts(self, *, non_root: bool = False) -> None:
        known_hosts = "~/.ssh/known_hosts"
        desc = self._desc(non_root=non_root)
        if self._is_file(known_hosts, non_root=non_root) and self._grep(
            "github.com", known_hosts, non_root=non_root
        ):
            _LOGGER.info("GitHub is already a known host for %r", desc)
            return
        _LOGGER.info("Adding GitHub to known hosts for %r...", desc)
        self._mkdir("~/.ssh", non_root=non_root)
        _ = self._run("ssh-keyscan github.com >> ~/.ssh/known_hosts", non_root=non_root)

    def _setup_bashrc(self, *, non_root: bool = False) -> None:
        self._copy_file_or_url(
            self._with_url(self.bashrc), "~/.bashrc", non_root=non_root
        )

    def _setup_git_config(self, *, non_root: bool = False) -> None:
        self._copy_file_or_url(
            self._with_url(self.git_config), "~/.config/git/config", non_root=non_root
        )

    def _install_starship(self, *, non_root: bool = False) -> None:
        desc = self._desc(non_root=non_root)
        if self._which("starship", non_root=non_root):
            _LOGGER.info("'starship' is already installed for %r", desc)
        else:
            _LOGGER.info("Installing 'starship' for %r...", desc)
            self._mkdir(self.path_local_bin, non_root=non_root)
            _ = self._run(
                f"curl -sS https://starship.rs/install.sh | sh -s -- -b {self.path_local_bin} -y",
                non_root=non_root,
            )
        self._copy_file_or_url(
            self._with_url(self.starship_toml),
            "~/.config/starship.toml",
            non_root=non_root,
        )

    def _install_runtime_tools(self) -> None:
        if not self.runtime:
            _LOGGER.info("Skipping runtime tools...")
            return
        _LOGGER.info("Installing runtime tools...")
        for cmd in ["age", "git", "jq", "just"]:
            _apt_install(cmd)
        for cmd, owner, repo, filename in [
            ("yq", "mikefarah", "yq", "yq_linux_amd64"),
            ("sops", "getsops", "sops", "sops-${tag}.linux.amd64"),
        ]:
            self._install_from_github(cmd, owner, repo, filename, non_root=True)
        self._install_direnv()
        self._install_uv()

    def _install_direnv(self) -> None:
        if self._which("direnv", non_root=True):
            _LOGGER.info("'direnv' is already installed for %r", self.non_root_username)
        else:
            _LOGGER.info("Installing 'direnv' for %r...", self.non_root_username)
            _ = self._run(
                "curl -sfL https://direnv.net/install.sh | bash",
                non_root=True,
                env={"bin_path": str(self.path_local_bin)},
            )
        self._copy_file_or_url(
            self._with_url(self.direnv_toml),
            "~/.config/direnv/direnv.toml",
            non_root=True,
        )

    def _install_uv(self) -> None:
        if self._which("uv", non_root=True):
            _LOGGER.info("'uv' is already installed for %r", self.non_root_username)
            return
        _LOGGER.info("Installing 'uv' for %r...", self.non_root_username)
        _ = self._run(
            "curl -LsSf https://astral.sh/uv/install.sh | sh -s",
            non_root=True,
            env={"UV_NO_MODIFY_PATH": "1"},
        )

    # utilities

    def _copy_file_or_url(
        self, from_: _PathLike, to: _PathLike, /, *, non_root: bool = False
    ) -> None:
        match from_:
            case Path():
                text_from = self._read_text(from_, non_root=non_root)
            case str():
                if self._is_file(from_, non_root=non_root):
                    text_from = self._read_text(from_, non_root=non_root)
                else:
                    with urlopen(from_) as resp:
                        text_from: str = resp.read().decode("utf-8").rstrip("\n")
            case never:
                assert_never(never)
        desc = self._desc(non_root=non_root)
        if self._is_file(to, non_root=non_root) and (
            self._read_text(to, non_root=non_root) == text_from
        ):
            _LOGGER.info("%r already up to date for %r", str(to), desc)
            return
        _LOGGER.info("Writing %r for %r...", str(to), desc)
        self._write_text(text_from, to, non_root=non_root)

    def _desc(self, *, non_root: bool = False) -> str:
        return self.non_root_username if non_root else "root"

    def _grep(self, text: str, path: _PathLike, /, *, non_root: bool = False) -> bool:
        return self._predicate(f"grep -q {text} {path}", non_root=non_root)

    def _install_from_github(
        self,
        cmd: str,
        owner: str,
        repo: str,
        filename: str,
        /,
        *,
        non_root: bool = False,
    ) -> None:
        desc = self._desc(non_root=non_root)
        if self._which(cmd, non_root=non_root):
            _LOGGER.info("%r is already installed for %r", cmd, self.non_root_username)
            return
        _LOGGER.info("Installing %r for %r...", cmd, desc)
        self._mkdir(self.path_local_bin, non_root=non_root)
        releases = f"{owner}/{repo}/releases"
        tag = self._run(
            f"curl -s https://api.github.com/repos/{releases}/latest | jq -r '.tag_name'",
            non_root=non_root,
        )
        filename_use = Template(filename).substitute(
            tag=tag, tag_without=tag.lstrip("v")
        )
        url = f"https://github.com/{releases}download/{tag}/{filename_use}"
        path = self.path_local_bin / cmd
        _ = self._run(
            f"curl --location {url} --output {path}",
            f"chmod +x {path}",
            non_root=non_root,
        )

    def _is_file(self, path: _PathLike, /, *, non_root: bool = False) -> bool:
        return self._predicate(f"[ -f {path} ]", non_root=non_root)

    def _mkdir(self, path: _PathLike, /, *, non_root: bool = False) -> None:
        _ = self._run(f"mkdir -p {path}", non_root=non_root)

    def _predicate(self, predicate: str, /, *, non_root: bool = False) -> bool:
        result = self._run(f"if {predicate}; then echo 1; fi", non_root=non_root)
        return result == "1"

    def _read_text(self, path: _PathLike, /, *, non_root: bool = False) -> str:
        return self._run(f"cat {path}", non_root=non_root)

    def _run(
        self,
        *cmds: str,
        non_root: bool = False,
        cwd: _PathLike | None = None,
        env: Mapping[str, str] | None = None,
        input_: str | None = None,
    ) -> str:
        cmds_use = (
            [f"su - {self.non_root_username} -c '{c}'" for c in cmds]
            if non_root
            else cmds
        )
        match cwd, non_root:
            case Path() | str() as cwd_use, _:
                ...
            case None, False:
                cwd_use = None
            case None, True:
                cwd_use = Path(f"/home/{self.non_root_username}")
            case never:
                assert_never(never)
        return _run(*cmds_use, cwd=cwd_use, env=env, input_=input_)

    @contextmanager
    def _temp_dir(self, *, non_root: bool = False) -> Iterator[Path]:
        path = Path(self._run("mktemp -d", non_root=non_root))
        try:
            yield path
        finally:
            _ = self._run(f"rm -rf {path}", non_root=non_root)

    def _which(self, cmd: str, /, *, non_root: bool = False) -> bool:
        try:
            result = self._run(f"which {cmd}", non_root=non_root)
        except CalledProcessError:
            return False
        return result != ""

    def _with_url(self, text: str, /) -> str:
        return Template(text).substitute(url=self.url)

    def _write_text(
        self, text: str, path: _PathLike, /, *, non_root: bool = False
    ) -> None:
        self._mkdir(Path(path).parent, non_root=non_root)
        _ = self._run(f"tee {path}", input_=text, non_root=non_root)


# main


def _apt_install(cmd: str, /) -> None:
    if which(cmd) is not None:
        _LOGGER.info("%r is already installed...", cmd)
        return
    _LOGGER.info("Installing %r...", cmd)
    _ = _run(f"apt install -y {cmd}")


def _run(
    *cmds: str,
    cwd: _PathLike | None = None,
    env: Mapping[str, str] | None = None,
    input_: str | None = None,
) -> str:
    results: list[str] = []
    for cmd in cmds:
        result = check_output(
            cmd,
            shell=True,
            cwd=cwd,
            env=None if env is None else {**environ, **env},
            input=input_,
            text=True,
        ).rstrip("\n")
        results.append(result)
    return "\n".join(results)


if __name__ == "__main__":
    settings = _Settings.parse()
    settings.install()
