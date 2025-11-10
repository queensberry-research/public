#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from contextlib import contextmanager
from dataclasses import dataclass
from ipaddress import IPv4Address
from logging import basicConfig, getLogger
from os import environ
from pathlib import Path
from socket import AF_INET, SOCK_DGRAM, gethostname, socket
from string import Template
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING, Any, Literal, Self, assert_never, get_args
from urllib.error import HTTPError
from urllib.request import urlopen

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


LOGGING_FORMAT = (
    f"[{{asctime}} ❯ {gethostname()} ❯ {{module}}:{{funcName}}:{{lineno}}] {{message}}"  # noqa: RUF001
)
basicConfig(format=LOGGING_FORMAT, datefmt="%Y-%m-%d %H:%M:%S", style="{", level="INFO")
_LOGGER = getLogger(__name__)
__all__ = [
    "CLI",
    "EVAL_DIRENV_EXPORT",
    "LOGGING_FORMAT",
    "NONROOT",
    "ROOT",
    "SUBNETS",
    "PathLike",
    "Subnet",
    "append_text",
    "chmod",
    "chown",
    "copy_file_or_url",
    "cp",
    "curl",
    "dirname",
    "get_perms",
    "get_subnet",
    "git",
    "grep",
    "have_command",
    "is_dir",
    "is_file",
    "is_symlink",
    "mkdir",
    "predicate",
    "read_link",
    "read_text",
    "replace_text",
    "rm",
    "run",
    "substitute",
    "sudo_cmd",
    "symlink",
    "temp_dir",
    "touch",
    "username",
    "uv",
    "write_text",
]
__version__ = "0.7.10"


# types


type PathLike = Path | str
type Subnet = Literal["qrt", "main", "test"]
type _Machine = Literal["proxmox", "vm"]
SUBNETS: list[Subnet] = list(get_args(Subnet.__value__))


# constants


EVAL_DIRENV_EXPORT = (
    'if command -v direnv >/dev/null 2>&1; then eval "$(direnv export bash)"; fi'
)
NONROOT = "nonroot"
ROOT = "root"
_FLAG_ROOT_PASSWORD = "--root-password"  # noqa: S105
_FLAG_PASSWORD = "--password"  # noqa: S105
_FLAG_TOOLS = "--tools"
_FLAG_DOCKER = "--docker"
_FLAG_GITHUB_REPO = "--github-repo"
_PATH_LOCAL_BIN = Path("~/.local/bin")
_QRT_DATASET = Path("/mnt/qrt-dataset")
_QRT_SECRETS = _QRT_DATASET / "qrt/secrets"
_SUBNET_MAPPING: dict[Subnet, int] = {"qrt": 20, "main": 50, "test": 60}
_URL_PUBLIC = (
    "https://raw.githubusercontent.com/queensberry-research/public/refs/$version"
)
_URL_CONFIGS = f"{_URL_PUBLIC}/configs"


# public


def append_text(path: PathLike, text: str, /, *, user: bool = False) -> None:
    _ = run(
        f"""\
cat >> {path} <<'APPENDTEXTEOF'
{text}
APPENDTEXTEOF""",
        user=user,
        eof="RUNEOF",
    )


def chmod(perms: str, path: PathLike, /, *, user: bool = False) -> None:
    _ = run(f"chmod {perms} {path}", user=user)


def chown(path: PathLike, /, *, user: bool = False) -> None:
    owner = NONROOT if user else ROOT
    _ = run(f"chown {owner}:{owner} {path}", user=user)


def copy_file_or_url(
    from_: PathLike,
    to: PathLike,
    /,
    *,
    user: bool = False,
    url_subs: Mapping[str, Any] | None = None,
    text_subs: Mapping[str, Any] | None = None,
    perms: str | None = None,
) -> None:
    match from_:
        case Path():
            text_from = read_text(from_, user=user)
        case str():
            if is_file(from_, user=user):
                text_from = read_text(from_, user=user)
            else:
                if url_subs is not None:
                    from_ = substitute(from_, **url_subs)
                try:
                    with urlopen(from_) as resp:
                        text_from: str = resp.read().decode("utf-8").rstrip("\n")
                except HTTPError:
                    _LOGGER.exception("Unable to find %r", from_)
                    raise
        case never:
            assert_never(never)
    if text_subs is not None:
        text_from = substitute(text_from, **text_subs)
    if (
        is_file(to, user=user)
        and (read_text(to, user=user) == text_from)
        and ((perms is None) or (get_perms(to, user=user) == perms))
    ):
        return
    _LOGGER.info("Writing %r for %r...", str(to), username(user=user))
    write_text(to, text_from, user=user, perms=perms)


def cp(
    from_: PathLike,
    to: PathLike,
    /,
    *,
    user: bool = False,
    recursive: bool = False,
    sudo: bool = False,
    ownership: bool = False,
) -> None:
    mkdir(to, parent=True, user=user)
    parts: list[str] = []
    parts.append("cp")
    if recursive:
        parts.append("-R")
    parts.extend([str(from_), str(to)])
    cmd = " ".join(parts)
    if sudo:
        cmd = sudo_cmd(cmd, user=user)
    _ = run(cmd, user=user)
    if ownership:
        chown(to, user=user)


def curl(
    cmd: str,
    /,
    *,
    user: bool = False,
    jq: bool = False,
    env: Mapping[str, str] | None = None,
    eof: str | None = None,
    cwd: PathLike | None = None,
    direnv: bool = False,
) -> str:
    _apt_install("curl")
    if jq:
        _apt_install("jq")
    return run(f"curl {cmd}", user=user, env=env, eof=eof, cwd=cwd, direnv=direnv)


def dirname(path: PathLike, /, *, user: bool = False) -> Path:
    return Path(run(f"dirname {path}", user=user))


def get_perms(path: PathLike, /, *, user: bool = False) -> str:
    result = run(f"ls -ld {path}", user=user)
    first = result.split()[0][1:10]
    u, g, o = [first[i : i + 3].replace("-", "") for i in [0, 3, 6]]
    return f"u={u},g={g},o={o}"


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
            if third == _SUBNET_MAPPING[subnet]:
                return subnet
        msg = f"Invalid IP; got {ip}"
        raise ValueError(msg) from None
    if subnet in SUBNETS:
        return subnet
    msg = f"Invalid subnet; got {subnet!r}"
    raise ValueError(msg)


def git(
    cmd: str,
    /,
    *,
    user: bool = False,
    env: Mapping[str, str] | None = None,
    eof: str | None = None,
    cwd: PathLike | None = None,
    direnv: bool = False,
) -> None:
    _apt_install("git")
    _ = run(f"git {cmd}", user=user, env=env, eof=eof, cwd=cwd, direnv=direnv)


def grep(path: PathLike, text: str, /, *, user: bool = False) -> bool:
    return is_file(path, user=user) and predicate(f"grep -q {text} {path}", user=user)


def have_command(cmd: str, /, *, user: bool = False) -> bool:
    try:
        result = run(f"which {cmd}", user=user)
    except CalledProcessError:
        return False
    return result != ""


def is_dir(path: PathLike, /, *, user: bool = False) -> bool:
    return predicate(f"[ -d {path} ]", user=user)


def is_file(path: PathLike, /, *, user: bool = False) -> bool:
    return predicate(f"[ -f {path} ]", user=user)


def is_symlink(path: PathLike, /, *, user: bool = False) -> bool:
    return predicate(f"[ -L {path} ]", user=user)


def mkdir(path: PathLike, /, *, parent: bool = False, user: bool = False) -> None:
    if (not parent) and (not is_dir(path, user=user)):
        _ = run(f"mkdir -p {path}", user=user)
    elif parent:
        mkdir(dirname(path, user=user), user=user)


def mv(from_: PathLike, to: PathLike, /, *, user: bool = False) -> None:
    _ = run(f"mv {from_} {to}", user=user)


def predicate(predicate: str, /, *, user: bool = False) -> bool:
    result = run(f"if {predicate}; then echo 1; fi", user=user)
    return result == "1"


def read_link(path: PathLike, /, *, user: bool = False) -> Path:
    return Path(run(f"readlink {path}", user=user))


def read_text(path: PathLike, /, *, user: bool = False) -> str:
    return run(f"cat {path}", user=user)


def replace_text(path: PathLike, /, *lines: str, user: bool = False) -> None:
    text = read_text(path, user=user)
    if (n := len(lines)) % 2 != 0:
        msg = f"Expected an even number of lines; got {n}"
        raise ValueError(msg)
    for i in range(0, n, 2):
        text = text.replace(lines[i], lines[i + 1])
    write_text(path, text, user=user)


def rm(path: PathLike, /, *, user: bool = False) -> bool:
    if is_file(path, user=user):
        _LOGGER.info("Removing %r...", str(path))
        _ = run(f"rm {path}", user=user)
        return True
    return False


def run(
    *cmds: str,
    user: bool = False,
    env: Mapping[str, str] | None = None,
    eof: str | None = None,
    cwd: PathLike | None = None,
    direnv: bool = False,
) -> str:
    template = """\
${user_cmd} ${quote} ${env_vars} bash -s ${quote} <<'${eof}'
if [ -f ~/.bashrc ]; then source ~/.bashrc; fi
${cd_cmd}
${direnv_cmd}
${cmds}
${eof}"""
    cmd = substitute(
        template,
        user_cmd=f"su - {NONROOT} -c" if user else "",
        quote="'" if user else "",
        env_vars="" if env is None else " ".join(f"{k}={v}" for k, v in env.items()),
        eof="EOF" if eof is None else eof,
        cd_cmd="" if cwd is None else f"cd {cwd} || exit 1",
        direnv_cmd=EVAL_DIRENV_EXPORT if direnv else "",
        cmds="\n".join(cmds),
    )
    return check_output(cmd, shell=True, text=True).rstrip("\n")


def substitute(text: str, /, **kwargs: Any) -> str:
    return Template(text).substitute(**kwargs)


def sudo_cmd(cmd: str, /, *, user: bool = False) -> str:
    return f"sudo {cmd}" if user else cmd


def symlink(
    from_: PathLike, to: PathLike, /, *, user: bool = False, sudo: bool = False
) -> None:
    if is_symlink(to, user=user) and (read_link(to, user=user)) == Path(from_):
        return
    cmd = f"ln -s {to} {from_}"
    if sudo:
        cmd = sudo_cmd(cmd, user=user)
    _ = run(cmd, user=user)


@contextmanager
def temp_dir(*, user: bool = False) -> Iterator[Path]:
    path = Path(run("mktemp -d", user=user))
    try:
        yield path
    finally:
        _ = run(f"rm -rf {path}", user=user)


def touch(path: PathLike, /, *, user: bool = False) -> None:
    mkdir(path, parent=True, user=user)
    _ = run(f"touch {path}", user=user)


def username(*, user: bool = False) -> str:
    return NONROOT if user else ROOT


def uv(
    cmd: str,
    /,
    *,
    user: bool = False,
    env: Mapping[str, str] | None = None,
    eof: str | None = None,
    cwd: PathLike | None = None,
    direnv: bool = False,
) -> str:
    _install_uv(user=user)
    return run(f"uv {cmd}", user=user, env=env, eof=eof, cwd=cwd, direnv=direnv)


def write_text(
    path: PathLike, text: str, /, *, user: bool = False, perms: str | None = None
) -> None:
    mkdir(path, parent=True, user=user)
    _ = run(
        f"""\
cat > {path} <<'WRITETEXTEOF'
{text}
WRITETEXTEOF""",
        user=user,
        eof="RUNEOF",
    )
    if perms is not None:
        chmod(perms, path, user=user)


def _install_uv(*, user: bool = False) -> None:
    if not have_command("uv", user=user):
        _LOGGER.info("Installing 'uv' for %r...", username(user=user))
        _ = curl(
            "-LsSf https://astral.sh/uv/install.sh | sh -s",
            user=user,
            env={"UV_NO_MODIFY_PATH": "1"},
        )


# public


@dataclass(order=True, unsafe_hash=True, kw_only=True)
class CLI:
    # fields

    machine: _Machine | None = None
    version: str | None = None
    root_password: str | None = None
    password: str | None = None
    tools: bool = False
    docker: bool = False
    github_repo: bool = False

    # class methods

    @classmethod
    def curl_cmd(
        cls,
        *,
        version: str | None = None,
        machine: _Machine | None = None,
        root_password: str | None = None,
        password: str | None = None,
        tools: bool = False,
        docker: bool = False,
        github_repo: bool = False,
    ) -> str:
        url = cls._substitute_version(f"{_URL_PUBLIC}/install.py", version=version)
        parts: list[str] = []
        if machine is not None:
            parts.extend(["--machine", machine])
        if root_password is not None:
            parts.extend([_FLAG_ROOT_PASSWORD, root_password])
        if password is not None:
            parts.extend([_FLAG_PASSWORD, password])
        if tools:
            parts.append(_FLAG_TOOLS)
        if docker:
            parts.append(_FLAG_DOCKER)
        if github_repo:
            parts.append(_FLAG_GITHUB_REPO)
        cmd = " ".join(parts)
        return f"""{{ command -v curl >/dev/null 2>&1 || {{ apt -y update && apt -y install curl; }}; }}; curl -fsLS {url} | python3 - {cmd}"""

    @classmethod
    def parse(cls) -> Self:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        cls._add_arguments(parser)
        subparser = parser.add_subparsers(dest="machine")
        proxmox = subparser.add_parser("proxmox", help="Setup a Proxmox host")
        cls._add_arguments(proxmox)
        vm = subparser.add_parser("vm", help="Setup a VM")
        cls._add_arguments(vm)
        return cls(**vars(parser.parse_args()))

    @classmethod
    def _add_arguments(cls, parser: ArgumentParser, /) -> None:
        _ = parser.add_argument(
            "--version", default=None, type=str, help=f"Version (latest {__version__})"
        )
        _ = parser.add_argument(
            _FLAG_ROOT_PASSWORD, default=None, type=str, help="Root password"
        )
        _ = parser.add_argument(
            _FLAG_PASSWORD, default=None, type=str, help="Non-root password"
        )
        _ = parser.add_argument(_FLAG_TOOLS, action="store_true", help="Install tools")
        _ = parser.add_argument(
            _FLAG_DOCKER, action="store_true", help="Install Docker"
        )
        _ = parser.add_argument(
            _FLAG_GITHUB_REPO,
            action="store_true",
            help="Use GitHub repo instead of GitLab",
        )

    @classmethod
    def _substitute_version(cls, text: str, /, *, version: str | None = None) -> str:
        return substitute(
            text, version="heads/master" if version is None else f"tags/{version}"
        )

    # instance methods

    def run(self) -> None:
        _LOGGER.info("Running version %s...", __version__)
        if self.version is not None:
            _ = run(
                self.curl_cmd(
                    version=self.version,
                    machine=self.machine,
                    root_password=self.root_password,
                    password=self.password,
                    tools=self.tools,
                    docker=self.docker,
                    github_repo=self.github_repo,
                )
            )
            return
        match self.machine:
            case "proxmox":
                _setup_proxmox(version=self.version)
            case "vm":
                _setup_vm()
            case None:
                ...
            case never:
                assert_never(never)
        if self.root_password is not None:
            _set_password(ROOT, self.root_password)
        _create_user()
        if self.password is not None:
            _set_password(NONROOT, self.password)
        _setup_sshd_config(version=self.version)
        _install_age()
        _install_sudo()
        for user in [False, True]:
            _setup_authorized_keys(user=user, version=self.version)
            _setup_age_key(user=user)
            _setup_bashrc(user=user, version=self.version)
            _setup_deploy_key(user=user)
            _setup_git_config(user=user, version=self.version)
            _setup_known_hosts(user=user)
            _setup_ssh_config(user=user, version=self.version)
            _setup_ssh_infra_repo(user=user, version=self.version)
            _setup_subnet_sh(user=user, version=self.version)
            _install_bump_my_version(user=user)
            _install_direnv(user=user, version=self.version)
            _install_neovim(user=user)
            _install_sops(user=user)
            _install_starship(user=user, version=self.version)
            _install_uv(user=user)
            _install_yq(user=user)
            _clone_infra_repo(user=user, github_repo=self.github_repo)
        if self.tools:
            _install_tools()
        if self.docker:
            _install_docker()


# private


def _apt_install(cmd: str, /) -> None:
    if not have_command(cmd):
        _LOGGER.info("Installing %r...", cmd)
        _ = run(f"apt install -y {cmd}")


def _apt_update() -> None:
    _LOGGER.info("Updating 'apt'...")
    _ = run("apt update -y")


def _clone_infra_repo(*, user: bool = False, github_repo: bool = False) -> None:
    path = "~/infra"
    if not is_dir(path, user=user):
        _LOGGER.info("Cloning 'infra' for %r...", username(user=user))
        if github_repo:
            key = "github-infra-mirror"
            owner = "queensberry-research"
            repo = "infra-mirror"
        else:
            key = "gitlab-infra"
            owner = "qrt-public"
            repo = "infra"
        url = f"ssh://git@{key}/{owner}/{repo}"
        git(f"clone --recurse-submodules {url} {path}", user=user)


def _create_user() -> None:
    try:
        _ = run(f"id -u {NONROOT}")
    except CalledProcessError:
        _LOGGER.info("Creating %r...", NONROOT)
        _ = run(
            f"useradd --create-home --shell /bin/bash {NONROOT}",
            f"usermod -aG sudo {NONROOT}",
        )


def _dpkg_install(path: PathLike, /) -> None:
    _ = run(f"dpkg -i {path}")


@contextmanager
def _github_binary(
    owner: str, repo: str, filename: str, /, *, user: bool = False
) -> Iterator[Path]:
    releases = f"{owner}/{repo}/releases"
    tag = curl(
        f"-s https://api.github.com/repos/{releases}/latest | jq -r '.tag_name'",
        jq=True,
        user=user,
    )
    filename_use = substitute(filename, tag=tag, tag_without=tag.lstrip("v"))
    url = f"https://github.com/{releases}/download/{tag}/{filename_use}"
    with temp_dir(user=user) as temp:
        path = temp / filename
        _ = curl(f"-L {url} -o {path}", user=user)
        _ = run(f"chmod +x {path}", user=user)
        yield path


def _github_install(
    cmd: str,
    owner: str,
    repo: str,
    filename: str,
    /,
    *,
    user: bool = False,
    dpkg: bool = False,
) -> None:
    if not have_command(cmd, user=user):
        _LOGGER.info("Installing %r for %r...", cmd, username(user=user))
        with _github_binary(owner, repo, filename, user=user) as binary:
            if not dpkg:
                mkdir(_PATH_LOCAL_BIN, user=user)
                mv(binary, _PATH_LOCAL_BIN / cmd, user=user)
            else:
                _dpkg_install(binary)


def _install_age() -> None:
    _apt_install("age")


def _install_bump_my_version(*, user: bool = False) -> None:
    if not have_command("bump-my-version", user=user):
        _LOGGER.info("Installing 'bump-my-version' for %r...", username(user=user))
        _ = uv("tool install bump-my-version", user=user)


def _install_direnv(*, user: bool = False, version: str | None = None) -> None:
    _github_install("direnv", "direnv", "direnv", "direnv.linux-amd64", user=user)
    copy_file_or_url(
        f"{_URL_CONFIGS}/direnv.toml",
        "~/.config/direnv/direnv.toml",
        user=user,
        url_subs={"version": _master_or_tag(version=version)},
    )


def _install_docker() -> None:
    if not have_command("docker"):
        _LOGGER.info("Installing 'docker'...")
        _ = run(
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
            f"usermod -aG docker {NONROOT}",
            eof="RUNEOF",
        )


def _install_fd() -> None:
    if not have_command("fd"):
        _apt_install("fd-find")
    symlink("/bin/fdfind", "/bin/fd")


def _install_neovim(*, user: bool = False) -> None:
    desc_ = username(user=user)
    if not have_command("nvim", user=user):
        _LOGGER.info("Installing 'nvim' for %r...", desc_)
        appimage = "nvim-linux-x86_64.appimage"
        with (
            _github_binary("neovim", "neovim", appimage) as binary,
            temp_dir(user=user) as tmp,
        ):
            mv(binary, tmp / appimage)
            _ = run(f"./{appimage} --appimage-extract", user=user, cwd=tmp)
            mkdir(_PATH_LOCAL_BIN, user=user)
            squashfs_root = "squashfs-root"
            mv(tmp / squashfs_root, _PATH_LOCAL_BIN, user=user)
        symlink(
            _PATH_LOCAL_BIN / squashfs_root / "usr/bin/nvim",
            _PATH_LOCAL_BIN / "nvim",
            user=user,
        )
    if not is_dir(config_nvim := "~/.config/nvim", user=user):
        _LOGGER.info("Installing 'lazyvim' for %r...", desc_)
        url = "https://github.com/LazyVim/starter"
        _ = git(f"clone {url} {config_nvim}", user=user)
        _ = run("nvim --headless '+Lazy! sync' +qa", user=user)


def _install_ripgrep() -> None:
    if not have_command("rg"):
        _apt_install("ripgrep")


def _install_starship(*, user: bool = False, version: str | None = None) -> None:
    if not have_command("starship", user=user):
        _LOGGER.info("Installing 'starship' for %r...", username(user=user))
        mkdir(_PATH_LOCAL_BIN, user=user)
        _ = curl(
            f"-sS https://starship.rs/install.sh | sh -s -- -b {_PATH_LOCAL_BIN} -y",
            user=user,
        )
    copy_file_or_url(
        f"{_URL_CONFIGS}/starship.toml",
        "~/.config/starship.toml",
        user=user,
        url_subs={"version": _master_or_tag(version=version)},
    )


def _install_sops(*, user: bool = False) -> None:
    _github_install("sops", "getsops", "sops", "sops-${tag}.linux.amd64", user=user)


def _install_sudo() -> None:
    _apt_install("sudo")
    if not predicate(f"id -nG {NONROOT} | grep -qw sudo"):
        _ = run(f"usermod -aG sudo {NONROOT}")


def _install_tools() -> None:
    _LOGGER.info("Installing tools...")
    for cmd in ["fzf", "just", "rsync", "vim"]:
        _apt_install(cmd)
    _install_fd()
    _install_ripgrep()
    for cmd, owner, repo, filename in [
        ("btm", "clementtsang", "bottom", "bottom_${tag}-1_amd64.deb"),
        ("delta", "dandavison", "delta", "git-delta_${tag}_amd64.deb"),
    ]:
        _github_install(cmd, owner, repo, filename, dpkg=True)


def _install_yq(*, user: bool = False) -> None:
    _github_install("yq", "mikefarah", "yq", "yq_linux_amd64", user=user)


def _master_or_tag(*, version: str | None = None) -> str:
    return "heads/master" if version is None else f"tags/{version}"


def _remove_sources() -> None:
    if any(
        rm(f"/etc/apt/sources.list.d/{name}.sources")
        for name in ["ceph", "pve-enterprise"]
    ):
        _apt_update()


def _set_password(username: str, password: str, /) -> None:
    _LOGGER.info("Setting %r password...", username)
    _ = run(f"echo '{username}:{password}' | chpasswd")


def _setup_age_key(*, user: bool = False) -> None:
    copy_file_or_url(
        _QRT_SECRETS / "age/secret-key.txt",
        "~/.config/sops/age/keys.txt",
        user=user,
        perms="u=rw,g=,o=",
    )


def _setup_authorized_keys(*, user: bool = False, version: str | None = None) -> None:
    copy_file_or_url(
        f"{_URL_CONFIGS}/authorized_keys",
        "~/.ssh/authorized_keys",
        user=user,
        url_subs={"version": _master_or_tag(version=version)},
    )


def _setup_bashrc(*, user: bool = False, version: str | None = None) -> None:
    copy_file_or_url(
        f"{_URL_CONFIGS}/.bashrc",
        "~/.bashrc",
        user=user,
        url_subs={"version": _master_or_tag(version=version)},
    )


def _setup_deploy_key(*, user: bool = False) -> None:
    for name in ["github-infra-mirror", "gitlab-infra"]:
        copy_file_or_url(
            _QRT_SECRETS / "deploy-keys/infra",
            f"~/.ssh/{name}",
            user=user,
            perms="u=rw,g=,o=",
        )


def _setup_git_config(*, user: bool = False, version: str | None = None) -> None:
    copy_file_or_url(
        f"{_URL_CONFIGS}/git-config",
        "~/.config/git/config",
        user=user,
        url_subs={"version": _master_or_tag(version=version)},
    )


def _setup_known_hosts(*, user: bool = False) -> None:
    mkdir(known_hosts := "~/.ssh/known_hosts", parent=True, user=user)
    if not grep(known_hosts, github := "github.com", user=user):
        _LOGGER.info("Adding %r to known hosts for %r...", github, username(user=user))
        _ = run(f"ssh-keyscan {github} >> {known_hosts}", user=user)
    if not grep(known_hosts, gitlab := "gitlab.qrt", user=user):
        _LOGGER.info("Adding %r to known hosts for %r...", gitlab, username(user=user))
        _ = run(f"ssh-keyscan -p 2424 {gitlab} >> {known_hosts}", user=user)


def _setup_proxmox(*, version: str | None = None) -> None:
    _remove_sources()
    subnet = get_subnet()
    copy_file_or_url(
        f"{_URL_CONFIGS}/resolv.conf",
        "/etc/resolv.conf",
        url_subs={"version": _master_or_tag(version=version)},
        text_subs={"n": _SUBNET_MAPPING[subnet], "subnet": subnet},
    )
    if not grep(storage_cfg := "/etc/pve/storage.cfg", "qrt-dataset"):
        copy_file_or_url(
            f"{_URL_CONFIGS}/storage.cfg",
            storage_cfg,
            url_subs={"version": _master_or_tag(version=version)},
            text_subs={"subnet": subnet},
        )


def _setup_ssh_config(*, user: bool = False, version: str | None = None) -> None:
    copy_file_or_url(
        f"{_URL_CONFIGS}/ssh-config",
        "~/.ssh/config",
        user=user,
        url_subs={"version": _master_or_tag(version=version)},
    )


def _setup_ssh_infra_repo(*, user: bool = False, version: str | None = None) -> None:
    for name in ["github-infra-mirror", "gitlab-infra"]:
        copy_file_or_url(
            f"{_URL_CONFIGS}/ssh-{name}",
            f"~/.ssh/config.d/{name}",
            user=user,
            url_subs={"version": _master_or_tag(version=version)},
        )


def _setup_sshd_config(*, version: str | None = None) -> None:
    copy_file_or_url(
        f"{_URL_CONFIGS}/sshd_config",
        "/etc/ssh/sshd_config.d/config",
        url_subs={"version": _master_or_tag(version=version)},
    )
    _ = run("systemctl restart ssh")


def _setup_subnet_sh(*, user: bool = False, version: str | None = None) -> None:
    try:
        subnet = get_subnet()
    except ValueError:
        return
    copy_file_or_url(
        f"{_URL_CONFIGS}/subnet.sh",
        "~/.bashrc.d/subnet.sh",
        user=user,
        url_subs={"version": _master_or_tag(version=version)},
        text_subs={"subnet": subnet},
    )


def _setup_vm() -> None:
    _apt_install("nfs-common")
    if not grep(fstab := "/etc/fstab", str(_QRT_DATASET)):
        mkdir(_QRT_DATASET)
        append_text(
            fstab,
            f"truenas.qrt:/mnt/qrt-pool/qrt-dataset {_QRT_DATASET} nfs vers=4 0 0",
        )
        _ = run("mount -a")


if __name__ == "__main__":
    cli = CLI.parse()
    cli.run()
