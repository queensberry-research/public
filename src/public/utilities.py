from __future__ import annotations

from dataclasses import field
from enum import StrEnum
from functools import wraps
from os import environ
from pathlib import Path
from tomllib import loads
from typing import TYPE_CHECKING, Any, Literal, assert_never, overload

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
    mkdir,
    replace_line,
    replace_lines,
    rm,
    run_command,
    run_commands,
    suppress_called_process_error,
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
from .types import SUBNETS

if TYPE_CHECKING:
    from collections.abc import Callable

    from .types import PathLike, Subnet


def get_subnet() -> Subnet:
    try:
        subnet = environ["SUBNET"]
    except KeyError:
        msg = "Env var 'SUBNET' not found"
        raise RuntimeError(msg) from None
    if subnet in SUBNETS:
        return subnet
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
def toml_bool(path: PathLike, expression: str, /) -> bool:
    return _toml_read(path, expression, bool)


@to_dataclass_field
def toml_enum[E: StrEnum](path: PathLike, expression: str, cls: type[E], /) -> E:
    (member,) = [e for e in cls if e.value == _toml_read(path, expression, str)]
    return member


@to_dataclass_field
def toml_float(path: PathLike, expression: str, /) -> float:
    return float(_toml_read(path, expression, (float, int)))


@to_dataclass_field
def toml_int(path: PathLike, expression: str, /) -> int:
    return _toml_read(path, expression, int)


@to_dataclass_field
def toml_path(path: PathLike, expression: str, /) -> Path:
    return Path(_toml_read(path, expression, str))


@to_dataclass_field
def toml_str(path: PathLike, expression: str, /) -> str:
    return _toml_read(path, expression, str)


@to_dataclass_field
def toml_str_nullable(path: PathLike, expression: str, /) -> str | None:
    return _toml_read(path, expression, str, nullable=True)


@to_dataclass_field
def toml_strs(path: PathLike, expression: str, /) -> tuple[str, ...]:
    result = _toml_read(path, expression, list)
    if all(isinstance(i, str) for i in result):
        return tuple(result)
    msg = f"Expected a list of strings at {expression!r}"
    raise TypeError(msg)


@overload
def _toml_read[T](path: PathLike, expression: str, cls: type[T], /) -> T: ...
@overload
def _toml_read[T](
    path: PathLike, expression: str, cls: type[T], /, *, nullable: Literal[True]
) -> T | None: ...
@overload
def _toml_read[T, U](
    path: PathLike, expression: str, cls: tuple[type[T], type[U]], /
) -> T | U: ...
def _toml_read[T, T1, T2](
    path: PathLike,
    expression: str,
    cls: type[T] | tuple[type[T1], type[T2]],
    /,
    *,
    nullable: bool = False,
) -> T | T1 | T2:
    data: Any = loads(full_path(path).read_text())
    keys = expression.split(".")
    while len(keys) >= 1:
        first, *rest = keys
        data, keys = data.get(first) if nullable else data[first], rest
    if isinstance(data, cls) or (nullable and (data is None)):
        return data
    match cls:
        case type():
            desc = f"{cls.__name__!r}"
        case type() as cls1, type() as cls2:
            desc = f"{cls1.__name__!r} or {cls2.__name__!r}"
        case never:
            assert_never(never)
    msg = f"Expected an object of type {desc} at {expression!r}; got {type(data).__name__!r}"
    raise TypeError(msg)


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
    "mkdir",
    "replace_line",
    "replace_lines",
    "rm",
    "run_command",
    "run_commands",
    "suppress_called_process_error",
    "symlink",
    "temp_environ",
    "to_dataclass_field",
    "toml_bool",
    "toml_enum",
    "toml_float",
    "toml_int",
    "toml_path",
    "toml_str",
    "toml_str_nullable",
    "toml_strs",
    "touch",
    "update_submodules",
    "uv_tool_install",
    "which",
    "write_template",
    "write_text",
    "yield_download",
    "yield_github_latest_download",
    "yield_tar_gz_contents",
]
