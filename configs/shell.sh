#!/usr/bin/env sh
# shellcheck disable=SC1091

# paths
export PATH="/usr/local/bin:${PATH}"
export PATH="${HOME}/.local/bin:${PATH}"
export PATH="${HOME}/.npm-global/bin:${PATH}"

if [ -f "${HOME}/.local/bin/env" ]; then
    . "${HOME}/.local/bin/env"
fi

# bashrc
resource_bashrc() { . "${HOME}/.bashrc"; }

# bat
if command -v batcat >/dev/null 2>&1; then
    alias bat='batcat'
fi

# cd
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# env vars
if command -v vim >/dev/null 2>&1; then
    export EDITOR=vim
    export VISUAL=vim
fi

# git
gl() { git log "$@"; }
gpl() { git pull --prune "$@"; }
gs() { git status "$@"; }
gsu() {
    git submodule update --init --recursive
    git submodule foreach --recursive 'git checkout --force master && git pull --prune'
}

# ls
l() { la "$@"; }
la() { ls -ahl --color=always "$@"; }

# public
update_public() {
    git -C "${HOME}/public" pull --prune
    git -C "${HOME}/public" submodule update --init --recursive
    git -C "${HOME}/public" submodule foreach --recursive 'git checkout --force master && git pull --prune'
    "${HOME}/public/scripts/local.sh"
    resource_bashrc
}

# starship
if [ -n "${BASH_VERSION-}" ] && command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
fi

# tail
tf() { tail -F --verbose "$@"; }

# vi mode
if [ -n "${BASH_VERSION-}" ]; then
    set -o vi
fi

# watch
wl() { watch -n0.5 --color --differences -- ls -al --color=yes --sort=time "$@"; }
