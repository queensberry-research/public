#!/usr/bin/env sh

set -eu

# paths
scripts=$(dirname -- "$(realpath -- "$0")")
repo_root=$(dirname -- "${scripts}")
configs="${repo_root}/configs"
xdg_config="${XDG_CONFIG_HOME:-${HOME}/.config}"

# apt
for executable in bat curl rsync vim; do
    if ! command -v "${executable}" >/dev/null 2>&1; then
        if [ "$(id -u)" = 0 ]; then
            apt-get update
            apt-get install -y "${executable}"
        else
            sudo apt-get update
            sudo apt-get install -y "${executable}"
        fi
    fi
done

# shell.sh
text=". ${configs}/shell.sh"
bashrc="${HOME}/.bashrc"
if ! grep -qF "${text}" "${bashrc}"; then
    # shellcheck disable=SC2016
    printf '%s\n' "${text}" >>"${bashrc}"
fi

# starship.toml
ln -sfn "${configs}/starship.toml" "${xdg_config}/starship.toml"
