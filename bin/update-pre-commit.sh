#!/usr/bin/env sh

pre-commit autoupdate

root=$(git rev-parse --show-toplevel)
filename='.pre-commit-config.yaml'
root_config="$root/$filename"
backup_config="$root/$filename.backup"
repo_config="$root/repo/pre-commit/$filename"
cp "$root_config" "$backup_config"
mv "$repo_config" "$root_config"
pre-commit autoupdate
mv "$root_config" "$repo_config"
mv "$backup_config" "$root_config"
