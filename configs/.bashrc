#!/usr/bin/env bash

# env
export PATH="$HOME/.local/bin${PATH:+:$PATH}"
export PATH="/usr/local/bin${PATH:+:$PATH}"

# local
if [ -d "$HOME/.bashrc.d" ]; then
	for file in "$HOME"/.bashrc.d/*; do
		# shellcheck source=/dev/null
		source "$file"
	done
fi

##############################################################################

# cd
alias ~='cd "$HOME"'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias cdr='cd $(git rev-parse --show-toplevel)'
cdh() {
	__current=$(pwd)
	cd / || return
	cd "$__current" || return
}

# bash
alias bashrc='$EDITOR "$HOME/.bashrc"'

# direnv
if command -v direnv >/dev/null 2>&1; then
	eval "$(direnv hook bash)"
fi

# editing
set -o vi
if command -v nvim >/dev/null 2>&1; then
	export EDITOR=nvim
	export VISUAL=nvim
elif command -v vim >/dev/null 2>&1; then
	export EDITOR=vim
	export VISUAL=vim
else
	export EDITOR=vi
	export VISUAL=vi
fi

# env
eg() { env | sort | grep -i "$@"; }

# fzf
if command -v fzf >/dev/null 2>&1; then
	eval "$(fzf --bash)"
fi

# git
alias gb='git branch --all --list --sort=-committerdate --verbose'
alias gc='git checkout'
alias gd='git diff'
alias gdc='git diff --cached'
alias gdm='git diff --origin/$(git symbolic-ref refs/remotes/origin/HEAD | sed "s#.*/##")'
alias gf='git fetch --all --force --prune --prune-tags --recurse-submodules=yes --tags'
alias gl='git log --abbrev-commit --decorate=short --pretty="format:%C(red)%h%C(reset) | %C(yellow)%d%C(reset) | %s | %Cgreen%cr%C(reset)"'
alias gpl='__git_branch_purge_local && git pull --all --ff-only --force --prune --tags'
alias gpw='watch -n2 "git pull --all --ff-only --force --prune --tags || git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)"'
alias gs='git status'
alias __git_fetch_and_purge='git fetch --all --force && __git_branch_purge_local'
gsu() {
	git submodule update --init --recursive || return $?
	# shellcheck disable=SC2016
	git submodule foreach --recursive '
        git checkout -- . &&
        git checkout $(git symbolic-ref refs/remotes/origin/HEAD | sed "s#.*/##") &&
		git pull --ff-only --force --prune --tags
    '
}
__git_branch_purge_local() { git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -D; }

# ls
alias l='ls -al --color=auto'

# nvim
if command -v nvim >/dev/null 2>&1; then
	alias n='nvim'
fi

# pct
if command -v pct >/dev/null 2>&1; then
	pct_restart() { pct stop "$1" && pct start "$1"; }
	pct_stop_destroy() { pct stop "$1" && pct destroy "$1"; }
fi

# proxmox
alias reboot-proxmox='echo 1 >/proc/sys/kernel/sysrq && echo b >/proc/sysrq-trigger'

# starship
if command -v starship >/dev/null 2>&1; then
	eval "$(starship init bash)"
fi

# tail
alias tf='tail -F'

# uv
if command -v uv >/dev/null 2>&1; then
	eval "$(uv generate-shell-completion bash)"
	eval "$(uvx --generate-shell-completion bash)"
fi

# vim
if command -v vim >/dev/null 2>&1; then
	alias v='vim'
fi

# watch
alias wl='watch n0.1 "ls -al"'
