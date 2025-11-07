#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from contextlib import contextmanager
from dataclasses import dataclass
from ipaddress import IPv4Address
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from shutil import which
from socket import AF_INET, SOCK_DGRAM, gethostname, socket
from string import Template
from subprocess import CalledProcessError, check_output
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    Self,
    assert_never,
    get_args,
    override,
)
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


type _Machine = Literal["proxmox", "lxc", "vm"]
type _PathLike = Path | str
type _Subnet = Literal["qrt", "main", "test"]
_MACHINES: list[_Machine] = list(get_args(_Machine.__value__))
_SUBNETS: list[_Subnet] = list(get_args(_Subnet.__value__))

# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True)
class Operator:
    # defaults
    default_mount_source: ClassVar[str] = "truenas.qrt:/mnt/qrt-pool/qrt-dataset"
    default_mount_target: ClassVar[Path] = Path("/mnt/qrt-dataset")
    default_mount_type: ClassVar[str] = "nfs"
    default_mount_options: ClassVar[str] = "vers=4"
    default_mount_backup: ClassVar[bool] = False
    default_mount_check: ClassVar[bool] = False
    default_path_qrt: ClassVar[Path] = Path("$mount/qrt")
    default_path_secrets: ClassVar[Path] = Path("$qrt/secrets")
    default_path_local_bin: ClassVar[Path] = Path("~/.local/bin")
    default_username: ClassVar[str] = "nonroot"

    # fields
    public_version: str = "0.5.131"
    mount_source: str = default_mount_source
    mount_target: Path = default_mount_target
    mount_type: str = default_mount_type
    mount_options: str = default_mount_options
    mount_backup: bool = default_mount_backup
    mount_check: bool = default_mount_check
    path_qrt: Path = default_path_qrt
    path_secrets: Path = default_path_secrets
    path_local_bin: Path = default_path_local_bin
    username: str = default_username

    # class methods

    @classmethod
    def parse(cls) -> Self:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        cls._add_arguments(parser)
        return cls(**vars(parser.parse_args()))

    @classmethod
    def _add_arguments(cls, parser: ArgumentParser, /) -> None:
        _ = parser.add_argument(
            "--mount-source",
            default=cls.default_mount_source,
            type=str,
            help="Mount source",
        )
        _ = parser.add_argument(
            "--mount-target",
            default=cls.default_mount_target,
            type=Path,
            help="Mount target",
        )
        _ = parser.add_argument(
            "--mount-type", default=cls.default_mount_type, type=str, help="Mount type"
        )
        _ = parser.add_argument(
            "--mount-options",
            default=cls.default_mount_options,
            type=str,
            help="Mount options",
        )
        _ = parser.add_argument(
            "--mount-backup", action="store_true", help="Mount backup"
        )
        _ = parser.add_argument(
            "--mount-check", action="store_true", help="Mount check"
        )
        _ = parser.add_argument(
            "--path-qrt",
            default=cls.default_path_qrt,
            type=Path,
            help="Path to the QRT dataset",
        )
        _ = parser.add_argument(
            "--path-secrets",
            default=cls.default_path_secrets,
            type=Path,
            help="Path to the secrets",
        )
        _ = parser.add_argument(
            "--path-local-bin",
            default=cls.default_path_local_bin,
            type=Path,
            help="Path to the local binaries",
        )
        _ = parser.add_argument(
            "--username",
            default=cls.default_username,
            type=str,
            help="Non-root username",
        )

    # instance methods

    def __post_init__(self) -> None:
        self.path_qrt = _substitute_path(self.path_qrt, mount=self.mount_target)
        self.path_secrets = _substitute_path(self.path_secrets, qrt=self.path_qrt)

    def _copy_file_or_url(
        self,
        from_: _PathLike,
        to: _PathLike,
        /,
        *,
        user: bool = False,
        substitute: Mapping[str, Any] | None = None,
    ) -> None:
        match from_:
            case Path():
                text_from = self._read_text(from_, user=user)
            case str():
                if self._is_file(from_, user=user):
                    text_from = self._read_text(from_, user=user)
                else:
                    with urlopen(from_) as resp:
                        text_from: str = resp.read().decode("utf-8").rstrip("\n")
            case never:
                assert_never(never)
        if substitute is not None:
            text_from = _substitute_str(text_from, **substitute)
        if self._is_file(to, user=user) and (
            self._read_text(to, user=user) == text_from
        ):
            return
        _LOGGER.info("Writing %r for %r...", str(to), self._desc(user=user))
        self._write_text(text_from, to, user=user)

    def _cp(self, from_: _PathLike, to: _PathLike, /, *, user: bool = False) -> None:
        _ = self._run(f"cp {from_} {to}", user=user)

    def _curl(
        self,
        cmd: str,
        /,
        *,
        user: bool = False,
        cwd: _PathLike | None = None,
        env: Mapping[str, str] | None = None,
        input_: str | None = None,
    ) -> str:
        if not self._which("curl"):
            _apt_install("curl")
        return self._run(f"curl {cmd}", user=user, cwd=cwd, env=env, input_=input_)

    def _desc(self, *, user: bool = False) -> str:
        return self.username if user else "root"

    def _dpkg_install(self, path: _PathLike, /, *, user: bool = False) -> None:
        cmd = f"dpkg -i {path}"
        if user:
            cmd = f"sudo {cmd}"
        _ = self._run(cmd, user=user)

    @contextmanager
    def _github_binary(
        self, owner: str, repo: str, filename: str, /, *, user: bool = False
    ) -> Iterator[Path]:
        releases = f"{owner}/{repo}/releases"
        tag = self._curl(
            f"-s https://api.github.com/repos/{releases}/latest | jq -r '.tag_name'",
            user=user,
        )
        filename_use = _substitute_str(filename, tag=tag, tag_without=tag.lstrip("v"))
        url = f"https://github.com/{releases}/download/{tag}/{filename_use}"
        with self._temp_dir(user=user) as temp:
            path = temp / filename
            _ = self._curl(f"-L {url} -o {path}", user=user)
            _ = self._run(f"chmod +x {path}", user=user)
            yield path

    def _github_install(
        self,
        cmd: str,
        owner: str,
        repo: str,
        filename: str,
        /,
        *,
        user: bool = False,
        dpkg: bool = False,
    ) -> None:
        if self._which(cmd, user=user):
            return
        _LOGGER.info("Installing %r for %r...", cmd, self._desc(user=user))
        with self._github_binary(owner, repo, filename, user=user) as binary:
            if not dpkg:
                self._mkdir(self.path_local_bin, user=user)
                self._mv(binary, self.path_local_bin / cmd, user=user)
            else:
                self._dpkg_install(binary, user=user)

    def _grep(self, path: _PathLike, text: str, /, *, user: bool = False) -> bool:
        return self._is_file(path, user=user) and self._predicate(
            f"grep -q {text} {path}", user=user
        )

    def _is_dir(self, path: _PathLike, /, *, user: bool = False) -> bool:
        return self._predicate(f"[ -d {path} ]", user=user)

    def _is_file(self, path: _PathLike, /, *, user: bool = False) -> bool:
        return self._predicate(f"[ -f {path} ]", user=user)

    def _is_symlink(self, path: _PathLike, /, *, user: bool = False) -> bool:
        return self._predicate(f"[ -L {path} ]", user=user)

    def _mkdir(self, path: _PathLike, /, *, user: bool = False) -> None:
        _ = self._run(f"mkdir -p {path}", user=user)

    def _mv(self, from_: _PathLike, to: _PathLike, /, *, user: bool = False) -> None:
        _ = self._run(f"mv {from_} {to}", user=user)

    def _predicate(self, predicate: str, /, *, user: bool = False) -> bool:
        result = self._run(f"if {predicate}; then echo 1; fi", user=user)
        return result == "1"

    def _read_link(self, path: _PathLike, /, *, user: bool = False) -> Path:
        return Path(self._run(f"readlink {path}", user=user))

    def _read_text(self, path: _PathLike, /, *, user: bool = False) -> str:
        return self._run(f"cat {path}", user=user)

    def _rm(self, path: _PathLike, /, *, user: bool = False) -> bool:
        if self._is_file(path, user=user):
            _LOGGER.info("Removing %r...", str(path))
            _ = self._run(f"rm {path}", user=user)
            return True
        return False

    def _run(
        self,
        *cmds: str,
        user: bool = False,
        cwd: _PathLike | None = None,
        env: Mapping[str, str] | None = None,
        input_: str | None = None,
    ) -> str:
        match cwd, user:
            case Path() | str() as cwd_use, _:
                ...
            case None, False:
                cwd_use = None
            case None, True:
                cwd_use = Path(f"/home/{self.username}")
            case never:
                assert_never(never)
        return _run(
            *cmds,
            user=self.username if user else None,
            cwd=cwd_use,
            env=env,
            input_=input_,
        )

    def _symlink(
        self, from_: _PathLike, to: _PathLike, /, *, user: bool = False
    ) -> None:
        if self._is_symlink(to, user=user) and (self._read_link(to, user=user)) == Path(
            from_
        ):
            return
        _LOGGER.info(
            "Symlinking %r -> %r for %r...", str(from_), str(to), self._desc(user=user)
        )
        _ = self._run(f"ln -s {from_} {to}", user=user)

    @contextmanager
    def _temp_dir(self, *, user: bool = False) -> Iterator[Path]:
        path = Path(self._run("mktemp -d", user=user))
        try:
            yield path
        finally:
            _ = self._run(f"rm -rf {path}", user=user)

    def _which(self, cmd: str, /, *, user: bool = False) -> bool:
        try:
            result = self._run(f"which {cmd}", user=user)
        except CalledProcessError:
            return False
        return result != ""

    def _write_text(self, text: str, path: _PathLike, /, *, user: bool = False) -> None:
        self._mkdir(Path(path).parent, user=user)
        _ = self._run(
            f"cat > {path} <<'WRITETEXTEOF'\n{text}\nWRITETEXTEOF",
            input_=text,
            user=user,
        )


@dataclass(order=True, unsafe_hash=True, kw_only=True)
class _Settings(Operator):
    # defaults
    default_subnets: ClassVar[dict[_Subnet, int]] = {"qrt": 20, "main": 50, "test": 60}
    default_url: ClassVar[str] = (
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master"
    )
    default_age_key: ClassVar[Path] = Path("$secrets/age/secret-key.txt")
    default_authorized_keys: ClassVar[str] = "$url/ssh/keys.txt"
    default_bashrc: ClassVar[str] = "$url/configs/.bashrc"
    default_deploy_key: ClassVar[Path] = Path("$secrets/deploy-keys/infra")
    default_direnv_toml: ClassVar[str] = "$url/configs/direnv.toml"
    default_git_config: ClassVar[str] = "$url/configs/git-config"
    default_resolv_conf: ClassVar[str] = "$url/configs/resolv.conf"
    default_sshd_config: ClassVar[str] = "$url/configs/sshd-config"
    default_starship_toml: ClassVar[str] = "$url/configs/starship.toml"
    default_storage_cfg: ClassVar[str] = "$url/ssh/storage.cfg"
    default_subnet_sh: ClassVar[str] = "$url/ssh/subnet.sh"

    # fields
    machine: _Machine | None = None
    root_password: str | None = None
    password: str | None = None
    url: str = default_url
    age_key: Path = default_age_key
    authorized_keys: str = default_authorized_keys
    bashrc: str = default_bashrc
    deploy_key: Path = default_deploy_key
    direnv_toml: str = default_direnv_toml
    git_config: str = default_git_config
    resolv_conf: str = default_resolv_conf
    sshd_config: str = default_sshd_config
    starship_toml: str = default_starship_toml
    storage_cfg: str = default_storage_cfg
    subnet_sh: str = default_subnet_sh
    tools: bool = False
    docker: bool = False

    # class methods

    @classmethod
    @override
    def _add_arguments(cls, parser: ArgumentParser, /) -> None:
        super()._add_arguments(parser)
        _ = parser.add_argument(
            "--machine",
            default=None,
            type=str,
            choices=_MACHINES,
            help="Setup a specific type of machine",
        )
        _ = parser.add_argument(
            "--root-password", default=None, type=str, help="'root' password"
        )
        _ = parser.add_argument(
            "--password", default=None, type=str, help="Non-root password"
        )
        _ = parser.add_argument(
            "--url", default=cls.default_url, type=str, help="Config repo URL"
        )
        _ = parser.add_argument(
            "--age-key", default=cls.default_age_key, type=Path, help="'age' key"
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
            "--deploy-key",
            default=cls.default_deploy_key,
            type=Path,
            help="'infra' repo deploy key",
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
            "--resolv-conf",
            default=cls.default_resolv_conf,
            type=str,
            help="'resolv.conf' file or URL",
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
            "--storage-cfg",
            default=cls.default_storage_cfg,
            type=str,
            help="'storage.cfg' file or URL",
        )
        _ = parser.add_argument(
            "--subnet-sh",
            default=cls.default_subnet_sh,
            type=str,
            help="'subnet.sh' file or URL",
        )
        _ = parser.add_argument("--tools", action="store_true", help="Install tools")
        _ = parser.add_argument("--docker", action="store_true", help="Install Docker")

    # instance methods

    @override
    def __post_init__(self) -> None:
        super().__post_init__()
        self.age_key = _substitute_path(self.age_key, secrets=self.path_secrets)
        self.authorized_keys = _substitute_str(self.authorized_keys, url=self.url)
        self.bashrc = _substitute_str(self.bashrc, url=self.url)
        self.deploy_key = _substitute_path(self.deploy_key, secrets=self.path_secrets)
        self.direnv_toml = _substitute_str(self.direnv_toml, url=self.url)
        self.git_config = _substitute_str(self.git_config, url=self.url)
        self.resolv_conf = _substitute_str(self.resolv_conf, url=self.url)
        self.sshd_config = _substitute_str(self.sshd_config, url=self.url)
        self.starship_toml = _substitute_str(self.starship_toml, url=self.url)
        self.storage_cfg = _substitute_str(self.storage_cfg, url=self.url)
        self.subnet_sh = _substitute_str(self.subnet_sh, url=self.url)

    def install(self) -> None:
        _LOGGER.info("Running version %s...", self.public_version)
        self._setup_machine()
        self._set_root_password()
        self._create_user()
        for cmd in ["git", "jq"]:
            _apt_install(cmd)
        self._setup_sshd_config()
        self._install_sudo()
        for user in [False, True]:
            self._setup_authorized_keys(user=user)
            self._setup_known_hosts(user=user)
            self._setup_bashrc(user=user)
            self._setup_git_config(user=user)
            self._install_neovim(user=user)
            self._install_starship(user=user)
        self._install_tools()
        self._install_docker()

    def _setup_machine(self) -> None:
        match self.machine:
            case "proxmox":
                self._setup_proxmox()
            case "lxc":
                self._setup_lxc()
            case "vm":
                self._setup_vm()
            case None:
                ...
            case never:
                assert_never(never)

    def _setup_proxmox(self) -> None:
        self._delete_proxmox_sources()
        subnet = self._get_subnet()
        self._copy_file_or_url(
            self.resolv_conf,
            "/etc/resolv.conf",
            substitute={"n": self.default_subnets[subnet], "subnet": subnet},
        )
        if not self._grep(storage_cfg := "/etc/pve/storage.cfg", "qrt-dataset"):
            self._copy_file_or_url(
                self.storage_cfg, storage_cfg, substitute={"subnet": subnet}
            )
        for user in [False, True]:
            self._copy_file_or_url(
                self.subnet_sh,
                "~/.bashrc.d/subnet.sh",
                user=user,
                substitute={"subnet": subnet},
            )

    def _delete_proxmox_sources(self) -> None:
        if any(
            self._rm(f"/etc/apt/sources.list.d/{name}.sources")
            for name in ["ceph", "pve-enterprise"]
        ):
            _apt_update()

    def _get_subnet(self) -> _Subnet:
        try:
            subnet = environ["SUBNET"]
        except KeyError:
            with socket(AF_INET, SOCK_DGRAM) as s:
                s.connect(("1.1.1.1", 80))
                ip = IPv4Address(s.getsockname()[0])
            _, _, third, _ = str(ip).split(".")
            third = int(third)
            for subnet in _SUBNETS:
                if third == self.default_subnets[subnet]:
                    return subnet
            msg = f"Invalid IP; got {ip}"
            raise ValueError(msg) from None
        if subnet in _SUBNETS:
            return subnet
        msg = f"Invalid subnet; got {subnet!r}"
        raise ValueError(msg)

    def _setup_lxc(self) -> None:
        _LOGGER.info("Setting up LXC...")

    def _setup_vm(self) -> None:
        _apt_install("nfs-common")
        if not self._grep(fstab := "/etc/fstab", str(self.mount_target)):
            self._mkdir(self.mount_target)
            parts = [
                self.mount_source,
                self.mount_target,
                self.mount_type,
                self.mount_options,
                int(self.mount_backup),
                int(self.mount_check),
            ]
            line = " ".join(map(str, parts))
            _ = self._run(f"echo {line} >> {fstab}", "mount -a")

    def _set_root_password(self) -> None:
        if (password := self.root_password) is None:
            return
        _LOGGER.info("Setting 'root' password...")
        _ = self._run(f"echo 'root:{password}' | chpasswd")

    def _create_user(self) -> None:
        username = self.username
        try:
            _ = self._run(f"id -u {username}")
        except CalledProcessError:
            _LOGGER.info("Creating %r...", username)
            _ = self._run(
                f"useradd --create-home --shell /bin/bash {username}",
                f"usermod -aG sudo {username}",
            )
        if (password := self.password) is None:
            return
        _LOGGER.info("Setting %r password...", username)
        _ = self._run(f"echo '{username}:{password}' | chpasswd")

    def _setup_sshd_config(self) -> None:
        self._copy_file_or_url(self.sshd_config, "/etc/ssh/sshd_config")

    def _install_sudo(self) -> None:
        _apt_install("sudo")
        _ = self._run(f"usermod -aG sudo {self.username}")

    def _setup_authorized_keys(self, *, user: bool = False) -> None:
        self._copy_file_or_url(
            self.authorized_keys, "~/.ssh/authorized_keys", user=user
        )

    def _setup_known_hosts(self, *, user: bool = False) -> None:
        if self._grep(known_hosts := "~/.ssh/known_hosts", "github.com", user=user):
            return
        _LOGGER.info("Adding GitHub to known hosts for %r...", self._desc(user=user))
        self._mkdir("~/.ssh", user=user)
        _ = self._run(f"ssh-keyscan github.com >> {known_hosts}", user=user)

    def _setup_bashrc(self, *, user: bool = False) -> None:
        self._copy_file_or_url(self.bashrc, "~/.bashrc", user=user)

    def _setup_git_config(self, *, user: bool = False) -> None:
        self._copy_file_or_url(self.git_config, "~/.config/git/config", user=user)

    def _install_neovim(self, *, user: bool = False) -> None:
        desc = self._desc(user=user)
        if not self._which("nvim", user=user):
            _LOGGER.info("Installing 'nvim' for %r...", desc)
            appimage = "nvim-linux-x86_64.appimage"
            with (
                self._github_binary("neovim", "neovim", appimage) as binary,
                self._temp_dir(user=user) as temp_dir,
            ):
                self._mv(binary, temp_dir / appimage)
                _ = self._run(
                    f"./{appimage} --appimage-extract", user=user, cwd=temp_dir
                )
                self._mkdir(self.path_local_bin, user=user)
                squashfs_root = "squashfs-root"
                self._mv(temp_dir / squashfs_root, self.path_local_bin, user=user)
            self._symlink(
                self.path_local_bin / squashfs_root / "usr/bin/nvim",
                self.path_local_bin / "nvim",
                user=user,
            )
        if not self._is_dir(config_nvim := "~/.config/nvim", user=user):
            _LOGGER.info("Installing 'lazyvim' for %r...", desc)
            url = "https://github.com/LazyVim/starter"
            _ = self._run(
                f"git clone {url} {config_nvim}",
                "nvim --headless '+Lazy! sync' +qa",
                env={"PATH": f"{self.path_local_bin}:{environ['PATH']}"},
                user=user,
            )

    def _install_starship(self, *, user: bool = False) -> None:
        if not self._which("starship", user=user):
            _LOGGER.info("Installing 'starship' for %r...", self._desc(user=user))
            self._mkdir(self.path_local_bin, user=user)
            _ = self._curl(
                f"-sS https://starship.rs/install.sh | sh -s -- -b {self.path_local_bin} -y",
                user=user,
            )
        self._copy_file_or_url(self.starship_toml, "~/.config/starship.toml", user=user)

    def _install_tools(self) -> None:
        if not self.tools:
            return
        _LOGGER.info("Installing tools...")
        for cmd in ["age", "fzf", "just", "ripgrep", "rsync", "vim"]:
            _apt_install(cmd)
        self._install_fd()
        for cmd, owner, repo, filename in [
            ("btm", "clementtsang", "bottom", "bottom_${tag}-1_amd64.deb"),
            ("delta", "dandavison", "delta", "git-delta_${tag}_amd64.deb"),
        ]:
            self._github_install(cmd, owner, repo, filename, dpkg=True)
        for cmd, owner, repo, filename in [
            ("sops", "getsops", "sops", "sops-${tag}.linux.amd64"),
            ("yq", "mikefarah", "yq", "yq_linux_amd64"),
        ]:
            self._github_install(cmd, owner, repo, filename, user=True)
        self._install_direnv(user=True)
        self._install_uv(user=True)
        self._install_bump_my_version(user=True)  # after uv

    def _install_fd(self) -> None:
        if not self._which("fd"):
            _LOGGER.info("Installing 'fd'...")
            _apt_install("fd-find")
        self._symlink("/bin/fdfind", "/bin/fd")

    def _install_bump_my_version(self, *, user: bool = False) -> None:
        if not self._which("bump-my-version", user=user):
            _LOGGER.info(
                "Installing 'bump-my-version' for %r...", self._desc(user=user)
            )
            _ = self._run("uv tool install bump-my-version", user=user)

    def _install_direnv(self, *, user: bool = False) -> None:
        if not self._which("direnv", user=user):
            _LOGGER.info("Installing 'direnv' for %r...", self._desc(user=user))
            _ = self._curl(
                "-sfL https://direnv.net/install.sh | bash",
                user=user,
                env={"bin_path": str(self.path_local_bin)},
            )
        self._copy_file_or_url(
            self.direnv_toml, "~/.config/direnv/direnv.toml", user=user
        )

    def _install_uv(self, *, user: bool = False) -> None:
        if not self._which("uv", user=user):
            _LOGGER.info("Installing 'uv' for %r...", self._desc(user=user))
            _ = self._curl(
                "-LsSf https://astral.sh/uv/install.sh | sh -s",
                user=user,
                env={"UV_NO_MODIFY_PATH": "1"},
            )

    def _install_docker(self) -> None:
        if self._which("docker"):
            return
        _LOGGER.info("Installing 'docker'...")
        _ = self._run(
            "for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do apt-get remove $pkg; done",
            "apt-get update",
            "apt-get install -y ca-certificates curl",
            "install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc",
            "chmod a+r /etc/apt/keyrings/docker.asc",
            """\
tee /etc/apt/sources.list.d/docker.sources <<DOCKEREOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
DOCKEREOF""",
            "apt-get update",
            "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            f"usermod -aG docker {self.username}",
        )


# main


def _apt_install(cmd: str, /) -> None:
    if which(cmd) is not None:
        return
    _LOGGER.info("Installing %r...", cmd)
    _ = _run(f"apt install -y {cmd}")


def _apt_update() -> None:
    _LOGGER.info("Updating 'apt'...")
    _ = _run("apt update -y")


def _run(
    *cmds: str,
    user: str | None = None,
    cwd: _PathLike | None = None,
    env: Mapping[str, str] | None = None,
    input_: str | None = None,
) -> str:
    results: list[str] = []
    user_use = "root" if user is None else user
    for cmd in cmds:
        cmd_use = f"su - {user_use} -c 'sh -s' <<'RUNEOF'"
        if cwd is not None:
            cmd_use = f"{cmd_use}\ncd {cwd} || exit 1"
        cmd_use = f"{cmd_use}\n{cmd}\nRUNEOF"
        result = check_output(
            cmd_use,
            shell=True,
            env=None if env is None else {**environ, **env},
            input=input_,
            text=True,
        ).rstrip("\n")
        results.append(result)
    return "\n".join(results)


def _substitute_path(path: _PathLike, /, **kwargs: Any) -> Path:
    return Path(Template(str(path)).substitute(**kwargs))


def _substitute_str(text: str, /, **kwargs: Any) -> str:
    return Template(text).substitute(**kwargs)


if __name__ == "__main__":
    settings = _Settings.parse()
    settings.install()
