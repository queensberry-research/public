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
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, assert_never, get_args
from urllib.error import HTTPError
from urllib.request import urlopen

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence


basicConfig(
    format=f"[{{asctime}} ❯ {gethostname()} ❯ {{module}}:{{funcName}}:{{lineno}}] {{message}}",  # noqa: RUF001
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level="INFO",
)
_LOGGER = getLogger(__name__)
__all__ = [
    "SUBNETS",
    "BaseOperator",
    "PathLike",
    "PublicOperator",
    "Subnet",
    "get_subnet",
    "run",
    "substitute",
]
__version__ = "0.6.44"


# types


type PathLike = Path | str
type Subnet = Literal["qrt", "main", "test"]
type _Machine = Literal["proxmox", "lxc", "vm"]
SUBNETS: list[Subnet] = list(get_args(Subnet.__value__))
_MACHINES: list[_Machine] = list(get_args(_Machine.__value__))


# classes


@dataclass(order=True, unsafe_hash=True, kw_only=True)
class BaseOperator:
    # constants
    mount_source: ClassVar[str] = "truenas.qrt:/mnt/qrt-pool/qrt-dataset"
    mount_target: ClassVar[Path] = Path("/mnt/qrt-dataset")
    mount_type: ClassVar[str] = "nfs"
    mount_options: ClassVar[str] = "vers=4"
    mount_backup: ClassVar[bool] = False
    mount_check: ClassVar[bool] = False
    path_qrt: ClassVar[Path] = mount_target / "qrt"
    path_secrets: ClassVar[Path] = path_qrt / "secrets"
    path_age_key: ClassVar[Path] = path_secrets / "age/secret-key.txt"
    path_deploy_key: ClassVar[Path] = path_secrets / "deploy-keys/infra"
    path_local_bin: ClassVar[Path] = Path("~/.local/bin")
    subnet_mapping: ClassVar[dict[Subnet, int]] = {"qrt": 20, "main": 50, "test": 60}
    username: ClassVar[str] = "nonroot"

    # instance methods

    def append_text(self, path: PathLike, text: str, /, *, user: bool = False) -> None:
        _ = self.run(
            f"""\
cat >> {path} <<'APPENDTEXTEOF'
{text}
APPENDTEXTEOF""",
            user=user,
            eof="RUNEOF",
        )

    def chmod(self, perms: str, path: PathLike, /, *, user: bool = False) -> None:
        _ = self.run(f"chmod {perms} {path}", user=user)

    def chown(
        self, owner: str, group: str, path: PathLike, /, *, user: bool = False
    ) -> None:
        _ = self.run(f"chown {owner}:{group} {path}", user=user)

    def copy_file_or_url(
        self,
        from_: PathLike,
        to: PathLike,
        /,
        *,
        user: bool = False,
        subs: Mapping[str, Any] | None = None,
        perms: str | None = None,
    ) -> None:
        match from_:
            case Path():
                text_from = self.read_text(from_, user=user)
            case str():
                if self.is_file(from_, user=user):
                    text_from = self.read_text(from_, user=user)
                else:
                    try:
                        with urlopen(from_) as resp:
                            text_from: str = resp.read().decode("utf-8").rstrip("\n")
                    except HTTPError:
                        _LOGGER.exception("Unable to find %r", from_)
                        raise
            case never:
                assert_never(never)
        if subs is not None:
            text_from = substitute(text_from, **subs)
        if (
            self.is_file(to, user=user)
            and (self.read_text(to, user=user) == text_from)
            and ((perms is None) or (self.perms(to, user=user) == perms))
        ):
            return
        _LOGGER.info("Writing %r for %r...", str(to), self.desc(user=user))
        self.write_text(to, text_from, user=user, perms=perms)

    def cp(self, from_: PathLike, to: PathLike, /, *, user: bool = False) -> None:
        _ = self.run(f"cp {from_} {to}", user=user)

    def curl(
        self,
        cmd: str,
        /,
        *,
        jq: bool = False,
        user: bool = False,
        env: Mapping[str, str] | None = None,
        path: Sequence[Path] | None = None,
        executable: str | None = None,
        eof: str | None = None,
        cwd: PathLike | None = None,
    ) -> str:
        if not self.which("curl", user=user):
            _apt_install("curl")
        if jq and not self.which("jq", user=user):
            _apt_install("jq")
        return self.run(
            f"curl {cmd}",
            user=user,
            env=env,
            path=path,
            executable=executable,
            eof=eof,
            cwd=cwd,
        )

    def desc(self, *, user: bool = False) -> str:
        return self.username if user else "root"

    def git(
        self,
        cmd: str,
        /,
        *,
        user: bool = False,
        env: Mapping[str, str] | None = None,
        path: Sequence[Path] | None = None,
        executable: str | None = None,
        eof: str | None = None,
        cwd: PathLike | None = None,
    ) -> None:
        if not self.which("git", user=user):
            _apt_install("git")
        _ = self.run(
            f"git {cmd}",
            user=user,
            env=env,
            path=path,
            executable=executable,
            eof=eof,
            cwd=cwd,
        )

    def grep(self, path: PathLike, text: str, /, *, user: bool = False) -> bool:
        return self.is_file(path, user=user) and self.predicate(
            f"grep -q {text} {path}", user=user
        )

    def is_dir(self, path: PathLike, /, *, user: bool = False) -> bool:
        return self.predicate(f"[ -d {path} ]", user=user)

    def is_file(self, path: PathLike, /, *, user: bool = False) -> bool:
        return self.predicate(f"[ -f {path} ]", user=user)

    def is_symlink(self, path: PathLike, /, *, user: bool = False) -> bool:
        return self.predicate(f"[ -L {path} ]", user=user)

    def mkdir(self, path: PathLike, /, *, user: bool = False) -> None:
        _ = self.run(f"mkdir -p {path}", user=user)

    def mv(self, from_: PathLike, to: PathLike, /, *, user: bool = False) -> None:
        _ = self.run(f"mv {from_} {to}", user=user)

    def perms(self, path: PathLike, /, *, user: bool = False) -> str:
        result = self.run(f"ls -ld {path}", user=user)
        first = result.split()[0][1:10]
        u, g, o = [first[i : i + 3].replace("-", "") for i in [0, 3, 6]]
        return f"u={u},g={g},o={o}"

    def predicate(self, predicate: str, /, *, user: bool = False) -> bool:
        result = self.run(f"if {predicate}; then echo 1; fi", user=user)
        return result == "1"

    def read_link(self, path: PathLike, /, *, user: bool = False) -> Path:
        return Path(self.run(f"readlink {path}", user=user))

    def read_text(self, path: PathLike, /, *, user: bool = False) -> str:
        return self.run(f"cat {path}", user=user)

    def replace_text(self, path: PathLike, /, *lines: str, user: bool = False) -> None:
        text = self.read_text(path, user=user)
        if (n := len(lines)) % 2 != 0:
            msg = f"Expected an even number of lines; got {n}"
            raise ValueError(msg)
        for i in range(0, n, 2):
            text = text.replace(lines[i], lines[i + 1])
        self.write_text(path, text, user=user)

    def rm(self, path: PathLike, /, *, user: bool = False) -> bool:
        if self.is_file(path, user=user):
            _LOGGER.info("Removing %r...", str(path))
            _ = self.run(f"rm {path}", user=user)
            return True
        return False

    def run(
        self,
        *cmds: str,
        user: bool = False,
        env: Mapping[str, str] | None = None,
        path: Sequence[Path] | None = None,
        executable: str | None = None,
        eof: str | None = None,
        cwd: PathLike | None = None,
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
        return run(
            *cmds,
            user=self.username if user else None,
            env=env,
            path=path,
            executable=executable,
            eof=eof,
            cwd=cwd_use,
        )

    def symlink(self, from_: PathLike, to: PathLike, /, *, user: bool = False) -> None:
        if self.is_symlink(to, user=user) and (self.read_link(to, user=user)) == Path(
            from_
        ):
            return
        _LOGGER.info(
            "Symlinking %r -> %r for %r...", str(from_), str(to), self.desc(user=user)
        )
        _ = self.run(f"ln -s {from_} {to}", user=user)

    @contextmanager
    def temp_dir(self, *, user: bool = False) -> Iterator[Path]:
        path = Path(self.run("mktemp -d", user=user))
        try:
            yield path
        finally:
            _ = self.run(f"rm -rf {path}", user=user)

    def which(self, cmd: str, /, *, user: bool = False) -> bool:
        try:
            result = self.run(f"which {cmd}", user=user)
        except CalledProcessError:
            return False
        return result != ""

    def write_text(
        self,
        path: PathLike,
        text: str,
        /,
        *,
        user: bool = False,
        perms: str | None = None,
    ) -> None:
        self.mkdir(Path(path).parent, user=user)
        _ = self.run(
            f"""\
cat > {path} <<'WRITETEXTEOF'
{text}
WRITETEXTEOF""",
            user=user,
            eof="RUNEOF",
        )
        if perms is not None:
            self.chmod(perms, path, user=user)


@dataclass(order=True, unsafe_hash=True, kw_only=True)
class PublicOperator(BaseOperator):
    # constants
    flag_machine: ClassVar[str] = "--machine"
    flag_root_password: ClassVar[str] = "--root-password"  # noqa: S105
    flag_password: ClassVar[str] = "--password"  # noqa: S105
    flag_tools: ClassVar[str] = "--tools"
    flag_docker: ClassVar[str] = "--docker"
    url_public: ClassVar[str] = (
        "https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master"
    )
    url_configs: ClassVar[str] = f"{url_public}/configs"
    url_authorized_keys: ClassVar[str] = f"{url_public}/ssh/keys.txt"
    url_bashrc: ClassVar[str] = f"{url_configs}/.bashrc"
    url_direnv_toml: ClassVar[str] = f"{url_configs}/direnv.toml"
    url_git_config: ClassVar[str] = f"{url_configs}/git-config"
    url_install: ClassVar[str] = f"{url_public}/install.py"
    url_resolv_conf: ClassVar[str] = f"{url_configs}/resolv.conf"
    url_ssh_config: ClassVar[str] = f"{url_configs}/ssh-config"
    url_ssh_github_infra_mirror: ClassVar[str] = (
        f"{url_configs}/ssh-github-infra-mirror"
    )
    url_sshd_config: ClassVar[str] = f"{url_configs}/sshd_config"
    url_starship_toml: ClassVar[str] = f"{url_configs}/starship.toml"
    url_storage_cfg: ClassVar[str] = f"{url_configs}/storage.cfg"
    url_subnet_sh: ClassVar[str] = f"{url_configs}/subnet.sh"

    # fields
    machine: _Machine | None = None
    root_password: str | None = None
    password: str | None = None
    tools: bool = False
    docker: bool = False

    # class methods

    @classmethod
    def curl_cmd(
        cls,
        *,
        machine: _Machine | None = None,
        root_password: str | None = None,
        password: str | None = None,
        tools: bool = False,
        docker: bool = False,
    ) -> str:
        parts: list[str] = []
        if machine is not None:
            parts.extend([cls.flag_machine, machine])
        if root_password is not None:
            parts.extend([cls.flag_root_password, root_password])
        if password is not None:
            parts.extend([cls.flag_password, password])
        if tools:
            parts.append(cls.flag_tools)
        if docker:
            parts.append(cls.flag_docker)
        cmd = " ".join(parts)
        return f"""{{ command -v curl >/dev/null 2>&1 || {{ apt -y update && apt -y install curl; }}; }}; curl -fsLS {cls.url_install} | python3 - {cmd}"""

    @classmethod
    def parse(cls) -> Self:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        _ = parser.add_argument(
            cls.flag_machine,
            default=None,
            type=str,
            choices=_MACHINES,
            help="Setup a specific type of machine",
        )
        _ = parser.add_argument(
            cls.flag_root_password, default=None, type=str, help="'root' password"
        )
        _ = parser.add_argument(
            cls.flag_password, default=None, type=str, help="Non-root password"
        )
        _ = parser.add_argument(
            cls.flag_tools, action="store_true", help="Install tools"
        )
        _ = parser.add_argument(
            cls.flag_docker, action="store_true", help="Install Docker"
        )
        return cls(**vars(parser.parse_args()))

    # instance methods

    def install(self) -> None:
        _LOGGER.info("Running version %s...", __version__)
        self._setup_machine()
        self._set_root_password()
        self._create_user()
        self._setup_sshd_config()
        _apt_install("age")
        self._install_sudo()
        for user in [False, True]:
            self._setup_authorized_keys(user=user)
            self._setup_age_key(user=user)
            self._setup_bashrc(user=user)
            self._setup_deploy_key(user=user)
            self._setup_git_config(user=user)
            self._setup_known_hosts(user=user)
            self._setup_ssh_config(user=user)
            self._setup_ssh_github_infra_mirror(user=user)
            self._install_direnv(user=user)
            self._install_neovim(user=user)
            self._install_sops(user=user)
            self._install_starship(user=user)
            self._install_uv(user=user)
            self._install_yq(user=user)
            self._install_bump_my_version(user=user)  # after uv
            self._clone_infra(user=user)
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
        subnet = get_subnet()
        self.copy_file_or_url(
            self.url_resolv_conf,
            "/etc/resolv.conf",
            subs={"n": self.subnet_mapping[subnet], "subnet": subnet},
        )
        if not self.grep(storage_cfg := "/etc/pve/storage.cfg", "qrt-dataset"):
            self.copy_file_or_url(
                self.url_storage_cfg, storage_cfg, subs={"subnet": subnet}
            )
        for user in [False, True]:
            self.copy_file_or_url(
                self.url_subnet_sh,
                "~/.bashrc.d/subnet.sh",
                user=user,
                subs={"subnet": subnet},
            )

    def _delete_proxmox_sources(self) -> None:
        if any(
            self.rm(f"/etc/apt/sources.list.d/{name}.sources")
            for name in ["ceph", "pve-enterprise"]
        ):
            _apt_update()

    def _setup_lxc(self) -> None:
        _LOGGER.info("Setting up LXC...")

    def _setup_vm(self) -> None:
        _apt_install("nfs-common")
        if not self.grep(fstab := "/etc/fstab", str(self.mount_target)):
            self.mkdir(self.mount_target)
            parts = [
                self.mount_source,
                self.mount_target,
                self.mount_type,
                self.mount_options,
                int(self.mount_backup),
                int(self.mount_check),
            ]
            line = " ".join(map(str, parts))
            _ = self.run(f"echo {line} >> {fstab}", "mount -a")

    def _set_root_password(self) -> None:
        if (password := self.root_password) is None:
            return
        _LOGGER.info("Setting 'root' password...")
        _ = self.run(f"echo 'root:{password}' | chpasswd")

    def _create_user(self) -> None:
        username = self.username
        try:
            _ = self.run(f"id -u {username}")
        except CalledProcessError:
            _LOGGER.info("Creating %r...", username)
            _ = self.run(
                f"useradd --create-home --shell /bin/bash {username}",
                f"usermod -aG sudo {username}",
            )
        if (password := self.password) is None:
            return
        _LOGGER.info("Setting %r password...", username)
        _ = self.run(f"echo '{username}:{password}' | chpasswd")

    def _setup_sshd_config(self) -> None:
        self.copy_file_or_url(self.url_sshd_config, "/etc/ssh/sshd_config")

    def _install_sudo(self) -> None:
        _apt_install("sudo")
        _ = self.run(f"usermod -aG sudo {self.username}")

    def _setup_age_key(self, *, user: bool = False) -> None:
        self.copy_file_or_url(
            self.path_age_key,
            "~/.config/sops/age/keys.txt",
            user=user,
            perms="u=rw,g=,o=",
        )

    def _setup_authorized_keys(self, *, user: bool = False) -> None:
        self.copy_file_or_url(
            self.url_authorized_keys, "~/.ssh/authorized_keys", user=user
        )

    def _setup_bashrc(self, *, user: bool = False) -> None:
        self.copy_file_or_url(self.url_bashrc, "~/.bashrc", user=user)

    def _setup_deploy_key(self, *, user: bool = False) -> None:
        self.copy_file_or_url(
            self.path_deploy_key,
            "~/.ssh/github-infra-mirror",
            user=user,
            perms="u=rw,g=,o=",
        )

    def _setup_git_config(self, *, user: bool = False) -> None:
        self.copy_file_or_url(self.url_git_config, "~/.config/git/config", user=user)

    def _setup_known_hosts(self, *, user: bool = False) -> None:
        if self.grep(known_hosts := "~/.ssh/known_hosts", "github.com", user=user):
            return
        _LOGGER.info("Adding GitHub to known hosts for %r...", self.desc(user=user))
        self.mkdir("~/.ssh", user=user)
        _ = self.run(f"ssh-keyscan github.com >> {known_hosts}", user=user)

    def _setup_ssh_config(self, *, user: bool = False) -> None:
        self.copy_file_or_url(self.url_ssh_config, "~/.ssh/config", user=user)

    def _setup_ssh_github_infra_mirror(self, *, user: bool = False) -> None:
        self.copy_file_or_url(
            self.url_ssh_github_infra_mirror,
            "~/.ssh/config.d/github-infra-mirror",
            user=user,
        )

    def _install_direnv(self, *, user: bool = False) -> None:
        self._github_install("direnv", "direnv", "direnv", "direnv.linux-amd64")
        self.copy_file_or_url(
            self.url_direnv_toml, "~/.config/direnv/direnv.toml", user=user
        )

    def _install_neovim(self, *, user: bool = False) -> None:
        desc = self.desc(user=user)
        if not self.which("nvim", user=user):
            _LOGGER.info("Installing 'nvim' for %r...", desc)
            appimage = "nvim-linux-x86_64.appimage"
            with (
                self._github_binary("neovim", "neovim", appimage) as binary,
                self.temp_dir(user=user) as temp_dir,
            ):
                self.mv(binary, temp_dir / appimage)
                _ = self.run(
                    f"./{appimage} --appimage-extract", user=user, cwd=temp_dir
                )
                self.mkdir(self.path_local_bin, user=user)
                squashfs_root = "squashfs-root"
                self.mv(temp_dir / squashfs_root, self.path_local_bin, user=user)
            self.symlink(
                self.path_local_bin / squashfs_root / "usr/bin/nvim",
                self.path_local_bin / "nvim",
                user=user,
            )
        if not self.is_dir(config_nvim := "~/.config/nvim", user=user):
            _LOGGER.info("Installing 'lazyvim' for %r...", desc)
            url = "https://github.com/LazyVim/starter"
            _ = self.git(f"clone {url} {config_nvim}", user=user)
            _ = self.run(
                "nvim --headless '+Lazy! sync' +qa",
                env={"PATH": f"{self.path_local_bin}:{environ['PATH']}"},
                user=user,
            )

    def _install_sops(self, *, user: bool = False) -> None:
        self._github_install(
            "sops", "getsops", "sops", "sops-${tag}.linux.amd64", user=user
        )

    def _install_starship(self, *, user: bool = False) -> None:
        if not self.which("starship", user=user):
            _LOGGER.info("Installing 'starship' for %r...", self.desc(user=user))
            self.mkdir(self.path_local_bin, user=user)
            _ = self.curl(
                f"-sS https://starship.rs/install.sh | sh -s -- -b {self.path_local_bin} -y",
                user=user,
            )
        self.copy_file_or_url(
            self.url_starship_toml, "~/.config/starship.toml", user=user
        )

    def _install_uv(self, *, user: bool = False) -> None:
        if not self.which("uv", user=user):
            _LOGGER.info("Installing 'uv' for %r...", self.desc(user=user))
            _ = self.curl(
                "-LsSf https://astral.sh/uv/install.sh | sh -s",
                user=user,
                env={"UV_NO_MODIFY_PATH": "1"},
            )

    def _install_yq(self, *, user: bool = False) -> None:
        self._github_install("yq", "mikefarah", "yq", "yq_linux_amd64", user=user)

    def _clone_infra(self, *, user: bool = False) -> None:
        path = "~/infra"
        if not self.is_dir(path, user=user):
            _LOGGER.info("Cloning 'infra' for %r...", self.desc(user=user))
            url = "ssh://git@github-infra-mirror/queensberry-research/infra-mirror"
            self.git(f"clone --recurse-submodules {url} {path}", user=user)

    def _install_tools(self) -> None:
        if not self.tools:
            return
        _LOGGER.info("Installing tools...")
        for cmd in ["fzf", "just", "ripgrep", "rsync", "vim"]:
            _apt_install(cmd)
        self._install_fd()
        for cmd, owner, repo, filename in [
            ("btm", "clementtsang", "bottom", "bottom_${tag}-1_amd64.deb"),
            ("delta", "dandavison", "delta", "git-delta_${tag}_amd64.deb"),
        ]:
            self._github_install(cmd, owner, repo, filename, dpkg=True)

    def _install_fd(self) -> None:
        if not self.which("fd"):
            _LOGGER.info("Installing 'fd'...")
            _apt_install("fd-find")
        self.symlink("/bin/fdfind", "/bin/fd")

    def _install_bump_my_version(self, *, user: bool = False) -> None:
        if not self.which("bump-my-version", user=user):
            _LOGGER.info("Installing 'bump-my-version' for %r...", self.desc(user=user))
            _ = self.run("uv tool install bump-my-version", user=user)

    def _install_docker(self) -> None:
        if self.which("docker"):
            return
        _LOGGER.info("Installing 'docker'...")
        _ = self.run(
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
            eof="RUNEOF",
        )

    @contextmanager
    def _github_binary(
        self, owner: str, repo: str, filename: str, /, *, user: bool = False
    ) -> Iterator[Path]:
        releases = f"{owner}/{repo}/releases"
        tag = self.curl(
            f"-s https://api.github.com/repos/{releases}/latest | jq -r '.tag_name'",
            jq=True,
            user=user,
        )
        filename_use = substitute(filename, tag=tag, tag_without=tag.lstrip("v"))
        url = f"https://github.com/{releases}/download/{tag}/{filename_use}"
        with self.temp_dir(user=user) as temp:
            path = temp / filename
            _ = self.curl(f"-L {url} -o {path}", user=user)
            _ = self.run(f"chmod +x {path}", user=user)
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
        if self.which(cmd, user=user):
            return
        _LOGGER.info("Installing %r for %r...", cmd, self.desc(user=user))
        with self._github_binary(owner, repo, filename, user=user) as binary:
            if not dpkg:
                self.mkdir(self.path_local_bin, user=user)
                self.mv(binary, self.path_local_bin / cmd, user=user)
            else:
                self._dpkg_install(binary, user=user)

    def _dpkg_install(self, path: PathLike, /, *, user: bool = False) -> None:
        cmd = f"dpkg -i {path}"
        if user:
            cmd = f"sudo {cmd}"
        _ = self.run(cmd, user=user)


# main


def run(
    *cmds: str,
    user: str | None = None,
    env: Mapping[str, str] | None = None,
    path: Sequence[PathLike] | None = None,
    executable: str | None = None,
    eof: str | None = None,
    cwd: PathLike | None = None,
) -> str:
    template = """\
${user_cmd} ${quote} ${env_vars} ${executable} -s ${quote} <<'${eof}'
${cd_cmd}
${cmds}
${eof}"""
    env_use = ({} if env is None else dict(env)) | (
        {} if path is None else {"PATH": ":".join([*map(str, path), environ["PATH"]])}
    )
    cmd = substitute(
        template,
        user_cmd="" if user is None else f"su - {user} -c",
        quote="" if user is None else "'",
        env_vars=" ".join(f"{k}={v}" for k, v in env_use.items()),
        executable="sh" if executable is None else executable,
        eof="EOF" if eof is None else eof,
        cd_cmd="" if cwd is None else f"cd {cwd} || exit 1",
        cmds="\n".join(cmds),
    )
    return check_output(cmd, shell=True, text=True).rstrip("\n")


def get_subnet() -> Subnet:
    try:
        subnet = environ["SUBNET"]
    except KeyError:
        with socket(AF_INET, SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 80))
            ip = IPv4Address(s.getsockname()[0])
        _, _, third, _ = str(ip).split(".")
        third = int(third)
        for subnet in SUBNETS:
            if third == BaseOperator.subnet_mapping[subnet]:
                return subnet
        msg = f"Invalid IP; got {ip}"
        raise ValueError(msg) from None
    if subnet in SUBNETS:
        return subnet
    msg = f"Invalid subnet; got {subnet!r}"
    raise ValueError(msg)


def substitute(text: str, /, **kwargs: Any) -> str:
    return Template(text).substitute(**kwargs)


def _apt_install(cmd: str, /) -> None:
    if which(cmd) is not None:
        return
    _LOGGER.info("Installing %r...", cmd)
    _ = run(f"apt install -y {cmd}")


def _apt_update() -> None:
    _LOGGER.info("Updating 'apt'...")
    _ = run("apt update -y")


if __name__ == "__main__":
    operator = PublicOperator.parse()
    operator.install()
