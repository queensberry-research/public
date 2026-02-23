#!/usr/bin/env sh

set -eu

script_dir=$(dirname -- "$(realpath -- "$0")")
src="${script_dir}/shell.sh"
dest="${XDG_CONFIG_HOME:-${HOME}/.config}/starship.sh"
ln -sfn "${src}" "${dest}"
