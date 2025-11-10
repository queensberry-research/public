#!/usr/bin/env bash

# env
export PATH="$HOME/.local/bin${PATH:+:$PATH}"
export PATH="/usr/local/bin${PATH:+:$PATH}"

# local
if [ -d "$HOME"/.bashrc.d ]; then
	for file in "$HOME"/.bashrc.d/*; do
		if [ -f "$file" ]; then
			# shellcheck source=/dev/null
			source "$file"
		fi
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
alias gb='git branch-default'
alias gc='git checkout'
alias gcm='git checkout master'
alias gd='git diff'
alias gdc='git diff --cached'
alias gdm='git diff-remote'
alias gf='git fetch-default'
alias gl='git log-default'
alias gpl='git pull-default'
alias gs='git status'
alias gsu='git submodule-update'
alias wgp='watch --color --interval 2 "git checkout master && git pull-default && git -c color.ui=always log-default -n10"'

# ls
alias l='ls -al --color=auto'

# nvim
if command -v nvim >/dev/null 2>&1; then
	alias n='nvim'
fi

# pct
if command -v pct >/dev/null 2>&1; then
	pct_restart() {
		pct stop "$1"
		pct start "$1"
	}
	pct_stop_destroy() {
		pct stop "$1"
		pct destroy "$1"
	}
fi

# proxmox
alias reboot-proxmox='echo 1 >/proc/sys/kernel/sysrq && echo b >/proc/sysrq-trigger'

# starship
if command -v starship >/dev/null 2>&1; then
	eval "$(starship init bash)"
fi

# tail
alias tf='tail -F --lines=100'

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
