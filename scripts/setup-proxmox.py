#!/usr/bin/env python3
from __future__ import annotations

from subprocess import CalledProcessError, check_call, check_output, run


def main() -> None:
    _ = check_call("apt install -y git", shell=True)


if __name__ == "__main__":
    main()
