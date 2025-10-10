#!/usr/bin/env sh

root=$(git rev-parse --show-toplevel)
cp "$root"/.pre-commit-config.yaml "$root"/.root.pre-commit-config.yaml
mv "$root"/pre-commit/.pre-commit-config.yaml "$root"/.pre-commit-config.yaml
pre-commit autoupdate
mv "$root"/.pre-commit-config.yaml "$root"/pre-commit/.pre-commit-config.yaml
mv "$root"/.root.pre-commit-config.yaml "$root"/.pre-commit-config.yaml
