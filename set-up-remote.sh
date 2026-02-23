#!/usr/bin/env sh

set -eu

if ! command -v git >/dev/null 2>&1; then
    if [ "$(id -u)" = 0 ]; then
        apt-get install -y git
    else
        sudo apt-get install -y git
    fi
fi

repo="${HOME}/starship"
if [ -d "${repo}" ]; then
    git -C "${repo}" fetch origin
    git -C "${repo}" reset --hard origin/master
    git -C "${repo}" submodule update --init --recursive
else
    git clone https://github.com/queensberry-research/starship.git "${repo}"
fi

"${repo}/set-up-local.sh"
