#!/usr/bin/env sh

set -eu

config="${XDG_CONFIG_HOME:-${HOME}/.config}"
link() {
    src="$(dirname -- "$(realpath -- "$0")")/$1"
    dest="${config}/$2"
    mkdir -p "$(dirname -- "${dest}")"
    ln -sfn "${src}" "${dest}"
}

if [ "$(id -u)" = 0 ]; then
    link starship.sh /etc/profile.d/starship.sh 2>/dev/null
else
    header='#### starship ####'
    bashrc="${HOME}/.bashrc"
    if ! grep -qF "${header}" "${bashrc}"; then
        # shellcheck disable=SC2016
        text='

#### starship #####
export PATH="/usr/local/bin:${PATH}"
if command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
fi
'
        printf '%\n' "${text}" >>"${bashrc}"
    fi
    link starship.sh /etc/profile.d/starship.sh 2>/dev/null
fi

link starship.toml "${config}/starship.toml"
