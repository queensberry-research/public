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
    default_bashrc: ClassVar[str] = "$url/configs/.bashrc"
    default_starship_toml: ClassVar[str] = "$url/configs/starship.toml"

    # fields

    root_password: str | None = None
    non_root_username: str = default_non_root_username
    non_root_password: str | None = None
    path_local_bin: Path = default_path_bin
    url: str = default_url
    bashrc: str = default_bashrc
    starship_toml: str = default_starship_toml
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
            "--bashrc",
            default=cls.default_bashrc,
            type=str,
            help="'.bashrc' file or URL",
        )
        _ = parser.add_argument(
            "--starship-toml",
            default=cls.default_starship_toml,
            type=str,
            help="'starship.toml' file or URL",
        )
        _ = parser.add_argument("--docker", action="store_true", help="Install Docker")
        return _Settings(**vars(parser.parse_args()))

    @property
    def non_root_home(self) -> Path:
        return Path(f"/home/{self.non_root_username}")

    @property
    def bashrc_use(self) -> str:
        return Template(self.bashrc).substitute(url=self.url)

    @property
    def starship_toml_use(self) -> str:
        return Template(self.starship_toml).substitute(url=self.url)

    # installer

    def install(self) -> None:
        self._set_root_password()
        self._create_user()
        _install_curl()
        for user in [None, settings.non_root_username]:
            _setup_bashrc(user=user, bashrc=settings.bashrc_use)
            _install_starship(
                user=user,
                path_bin=settings.path_local_bin,
                starship_toml=settings.starship_toml_use,
            )

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

    def _setup_bashrc(*, non_root: bool = False) -> None:
        _LOGGER.info("Setting up '.bashrc' for %r", self._desc(non_root=non_root))
        self._copy_file_or_url(self.bashrc, "~/.bashrc", non_root=non_root)

    def _install_starship(self, *, non_root: bool = False) -> None:
        user_for = "root" if user is None else user
        if _which("starship", user=user):
            _LOGGER.info("'starship' already installed for %r...", user_for)
        else:
            _LOGGER.info("Installing 'starship' for %r...", user_for)
            _ = _run_commands(
                f"mkdir -p {path_bin}",
                f"curl -sS https://starship.rs/install.sh | sh -s -- -b {path_bin} -y",
                user=user,
            )

    # utilities

    def _copy_file_or_url(
        self, from_: _PathLike, to: _PathLike, /, *, non_root: bool = False
    ) -> None:
        match self:
            case Path():
                text_from = self._read_text(non_root=non_root)
            case str():
                if _is_file(self, user=user):
                    text_from = _read_text(self, user=user)
                else:
                    with urlopen(self) as response:
                        text_from: str = response.read().decode("utf-8")
            case never:
                assert_never(never)
        if _is_file(to, user=user) and (_read_text(to, user=user) == text_from):
            _LOGGER.info("%r exists and is already copied", str(to))
            return
        _LOGGER.info("Writing %r...", str(to))
        _write_text(text_from, to)

    def _desc(self, *, non_root: bool = False) -> str:
        return self.non_root_username if non_root else "root"

    def _is_file(self, path: _PathLike, /, *, non_root: bool = False) -> bool:
        result = self._run(f"if [ -f {path} ]; then echo 1; fi", non_root=non_root)
        return result == "1"

    def _read_text(self, path: _PathLike, /, *, non_root: bool = False) -> str:
        return self._run(f"cat {path}", non_root=non_root)

    def _run(
        self,
        *cmds: str,
        non_root: bool = False,
        cwd: _PathLike | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str:
        results: list[str] = []
        match cwd, non_root:
            case Path() | str() as cwd_use, _:
                ...
            case None, False:
                cwd_use = None
            case None, True:
                cwd_use = self.non_root_home
            case never:
                assert_never(never)
        for cmd in cmds:
            result = check_output(
                cmd,
                executable=which("bash"),
                shell=True,
                cwd=cwd_use,
                env=None if env is None else {**environ, **env},
                text=True,
                user=self.non_root_username if non_root else None,
            ).rstrip("\n")
            results.append(result)
        return "\n".join(results)

    def _which(self, cmd: str, /, *, non_root: bool = False) -> bool:
        try:
            result = self._run(f"which {cmd}", non_root=non_root)
        except CalledProcessError:
            return False
        return result != ""

    def _write_text(
        self, text: str, path: _PathLike, /, *, non_root: bool = False
    ) -> None:
        _ = self._run(f"echo {text} > {path}", non_root=non_root)


# main


def _install_curl() -> None:
    if which("curl") is not None:
        _LOGGER.info("'curl' already installed...")
        return
    _LOGGER.info("Installing 'curl'...")
    _ = check_output("apt install -y curl", shell=True)


if __name__ == "__main__":
    settings = _Settings.parse()
    settings.install()
