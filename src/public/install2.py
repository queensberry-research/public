from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
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
    from collections.abc import Mapping


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
        _install_curl()
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
        _install_age()
        self._install_direnv()

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
                    with urlopen(from_) as response:
                        text_from: str = response.read().decode("utf-8").rstrip("\n")
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

    def _expand(self, path: _PathLike, /, *, non_root: bool = False) -> Path:
        return Path(self._run(f"echo {path}", non_root=non_root))

    def _grep(self, text: str, path: _PathLike, /, *, non_root: bool = False) -> bool:
        return self._predicate(f"grep -q {text} {path}", non_root=non_root)

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
        results: list[str] = []
        match cwd, non_root:
            case Path() | str() as cwd_use, _:
                ...
            case None, False:
                cwd_use = None
            case None, True:
                cwd_use = Path(f"/home/{self.non_root_username}")
            case never:
                assert_never(never)
        for cmd in cmds:
            cmd_use = f"su - {self.non_root_username} -c '{cmd}'" if non_root else cmd
            result = check_output(
                cmd_use,
                shell=True,
                cwd=cwd_use,
                env=None if env is None else {**environ, **env},
                input=input_,
                text=True,
            ).rstrip("\n")
            results.append(result)
        return "\n".join(results)

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


def _install_curl() -> None:
    if which("curl") is not None:
        _LOGGER.info("'curl' is already installed...")
        return
    _LOGGER.info("Installing 'curl'...")
    _ = check_output("apt install -y curl", shell=True)


def _install_age() -> None:
    if which("age") is not None:
        _LOGGER.info("'age' is already installed...")
    else:
        _LOGGER.info("Installing 'age'...")
        _ = check_output("apt install -y age", shell=True)


if __name__ == "__main__":
    settings = _Settings.parse()
    settings.install()
