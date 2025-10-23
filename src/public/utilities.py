from __future__ import annotations

from dataclasses import field
from functools import wraps
from json import loads
from os import environ
from pathlib import Path
from re import search
from typing import TYPE_CHECKING, Literal

from .installer_utilities import (
    EVAL_DIRENV_EXPORT,
    SOURCE_BASHRC,
    TemporaryDirectory,
    append_contents,
    apt_install,
    apt_update,
    brew_install,
    brew_installed,
    check_for_commands,
    chmod,
    chown,
    contains_line,
    cp,
    download,
    dpkg_install,
    full_path,
    get_latest_tag,
    git_pull,
    have_command,
    is_root,
    luarocks_install,
    mac_app_exists,
    replace_line,
    replace_lines,
    rm,
    run_command,
    run_commands,
    symlink,
    temp_environ,
    touch,
    update_submodules,
    uv_tool_install,
    which,
    write_template,
    write_text,
    yield_download,
    yield_github_latest_download,
    yield_tar_gz_contents,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .types import PathLike, Subnet


type _Format = Literal["yaml", "json"]


def get_subnet() -> Subnet:
    try:
        subnet = environ["SUBNET"]
    except KeyError:
        msg = "Env var 'SUBNET' not found"
        raise RuntimeError(msg) from None
    if subnet == "main":
        return "main"
    if subnet == "test":
        return "test"
    msg = f"Invalid subnet; got {subnet!r}"
    raise RuntimeError(msg)


def to_dataclass_field[**P, T](func: Callable[P, T], /) -> Callable[P, T]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return field(default_factory=lambda: func(*args, **kwargs))

    return wrapped


def field_df[T](default_factory: Callable[[], type[T]], /) -> T:
    return field(default_factory=lambda: default_factory()())


@to_dataclass_field
def yq_bool(path: PathLike, expression: str, /) -> bool:
    match _run_yq(path, expression):
        case "true":
            return True
        case "false":
            return False
        case result:
            msg = f"Invalid boolean; got {result!r}"
            raise ValueError(msg)


@to_dataclass_field
def yq_float(path: PathLike, expression: str, /) -> float:
    return float(_run_yq(path, expression))


@to_dataclass_field
def yq_int(path: PathLike, expression: str, /) -> int:
    return int(_run_yq(path, expression))


@to_dataclass_field
def yq_path(path: PathLike, expression: str, /) -> Path:
    return Path(_run_yq(path, expression))


@to_dataclass_field
def yq_str(path: PathLike, expression: str, /) -> str:
    return _run_yq(path, expression)


@to_dataclass_field
def yq_strs(path: PathLike, expression: str, /) -> tuple[str, ...]:
    return tuple(loads(_run_yq(path, expression, format_="json")))


def _run_yq(path: PathLike, expression: str, /, *, format_: _Format = "yaml") -> str:
    result = run_command(
        f"yq --input-format toml --output-format {format_} {expression} {path}",
        skip_log=True,
    )
    if search("null", result):
        msg = f"Expression {expression!r} not found in {str(path)!r}"
        raise KeyError(msg)
    return result


__all__ = [
    "EVAL_DIRENV_EXPORT",
    "SOURCE_BASHRC",
    "TemporaryDirectory",
    "append_contents",
    "apt_install",
    "apt_update",
    "brew_install",
    "brew_installed",
    "check_for_commands",
    "chmod",
    "chown",
    "contains_line",
    "cp",
    "download",
    "dpkg_install",
    "field_df",
    "full_path",
    "get_latest_tag",
    "get_subnet",
    "git_pull",
    "have_command",
    "is_root",
    "luarocks_install",
    "mac_app_exists",
    "replace_line",
    "replace_lines",
    "rm",
    "run_command",
    "run_commands",
    "symlink",
    "temp_environ",
    "to_dataclass_field",
    "touch",
    "update_submodules",
    "uv_tool_install",
    "which",
    "write_template",
    "write_text",
    "yield_download",
    "yield_github_latest_download",
    "yield_tar_gz_contents",
    "yq_bool",
    "yq_float",
    "yq_int",
    "yq_path",
    "yq_str",
    "yq_strs",
]
