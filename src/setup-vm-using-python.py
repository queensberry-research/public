#!/usr/bin/env python3.13
from argparse import ArgumentParser
from dataclasses import dataclass


@dataclass(order=True, unsafe_hash=True, kw_only=True, slots=True)
class Settings:
    aliases: bool = False


def main(settings: Settings, /) -> None:
    pass


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--alias",
        dest="alias",
        action="store_true",
        help="Add aliases (default: disabled)",
    )
    args = parser.parse_args()
    cfg = Settings(
        aliases=args.alias,
    )
    main(cfg)
