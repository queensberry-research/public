#!/usr/bin/env sh

set -eu

# paths
scripts=$(dirname -- "$(realpath -- "$0")")
repo_root=$(dirname -- "${scripts}")
configs="${repo_root}/configs"
submodules="${repo_root}/submodules"
xdg_config="${XDG_CONFIG_HOME:-${HOME}/.config}"

# apt
if [ "$(id -u)" = 0 ]; then
    apt-get update 1>/dev/null
else
    sudo apt-get update 1>/dev/null
fi
for exec_pkg in batcat/bat curl/curl rg/ripgrep rsync/rsync vim/vim; do
    executable="${exec_pkg%%/*}"
    if ! command -v "${executable}" >/dev/null 2>&1; then
        package="${exec_pkg#*/}"
        if [ "$(id -u)" = 0 ]; then
            apt-get update
            apt-get install -y "${package}"
        else
            sudo apt-get update
            sudo apt-get install -y "${package}"
        fi
    fi
done
if [ "$(id -u)" = 0 ]; then
    apt-get upgrade -y
    apt-get autoremove -y
else
    sudo apt-get upgrade -y
    sudo apt-get autoremove -y
fi

# authorized keys
auth_keys="${HOME}/.ssh/authorized_keys"
mkdir -p "$(dirname "${auth_keys}")"
while IFS= read -r line; do
    [ -z "${line}" ] && continue
    if ! grep -Fxq -- "${line}" "${auth_keys}"; then
        printf '%s\n' "${line}" >>"${auth_keys}"
    fi
done <"${submodules}/authorized-keys/authorized_keys"

# shell.sh
text="[ -f \"${configs}/shell.sh\" ] && . \"${configs}/shell.sh\""
bashrc="${HOME}/.bashrc"
if ! grep -Fqx "${text}" "${bashrc}"; then
    # shellcheck disable=SC2016
    printf '%s\n' "${text}" >>"${bashrc}"
fi

# starship.toml
ln -sfn "${configs}/starship.toml" "${xdg_config}/starship.toml"
