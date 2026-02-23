#!/usr/bin/env sh
# shellcheck disable=SC1091

# paths
export PATH="/usr/local/bin:${PATH}"
export PATH="${HOME}/.local/bin:${PATH}"
export PATH="${HOME}/.npm-global/bin:${PATH}"

if [ -f "${HOME}/.local/bin/env" ]; then
    . "${HOME}/.local/bin/env"
fi

# env vars
export EDITOR=vim
export VISUAL=vim

# ls
l() { la "$@"; }
la() { ls -ahl --color=always "$@"; }

# starship
if [ -n "${BASH_VERSION-}" ] && command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
fi
