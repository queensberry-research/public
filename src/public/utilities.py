from __future__ import annotations

from dataclasses import field
from functools import wraps
from json import loads
from pathlib import Path
from re import search
from typing import TYPE_CHECKING, Literal

from .installer_utilities import run_command

if TYPE_CHECKING:
    from collections.abc import Callable

    from .types import PathLike


type _Format = Literal["yaml", "json"]


def _to_field[**P, T](func: Callable[P, T], /) -> Callable[P, T]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return field(default_factory=lambda: func(*args, **kwargs))

    return wrapped


def field_df[T](default_factory: Callable[[], type[T]], /) -> T:
    return field(default_factory=lambda: default_factory()())


@_to_field
def yq_bool(path: PathLike, expression: str, /) -> bool:
    match _run_yq(path, expression):
        case "true":
            return True
        case "false":
            return False
        case result:
            msg = f"Invalid boolean; got {result!r}"
            raise ValueError(msg)


@_to_field
def yq_float(path: PathLike, expression: str, /) -> float:
    return float(_run_yq(path, expression))


@_to_field
def yq_int(path: PathLike, expression: str, /) -> int:
    return int(_run_yq(path, expression))


@_to_field
def yq_path(path: PathLike, expression: str, /) -> Path:
    return Path(_run_yq(path, expression))


@_to_field
def yq_str(path: PathLike, expression: str, /) -> str:
    return _run_yq(path, expression)


@_to_field
def yq_strs(path: PathLike, expression: str, /) -> tuple[str, ...]:
    return tuple(loads(_run_yq(path, expression, format_="json")))


def _run_yq(path: PathLike, expression: str, /, *, format_: _Format = "yaml") -> str:
    result = run_command(
        f"yq --input-format toml --output-format {format_} {expression} {path}"
    )
    if search("null", result):
        msg = f"Expression {expression!r} not found in {str(path)!r}"
        raise ValueError(msg)
    return result


__all__ = [
    "field_df",
    "run_command",
    "yq_bool",
    "yq_float",
    "yq_int",
    "yq_path",
    "yq_str",
    "yq_strs",
]
