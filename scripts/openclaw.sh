#!/usr/bin/env sh
# shellcheck disable=SC1090

#### public ###################################################################
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/scripts/remote.sh | sh

#### openclaw #################################################################
if ! command -v openclaw >/dev/null 2>&1; then
    curl -fsSL https://openclaw.ai/install.sh | bash
fi

#### restoration ##############################################################
# PATH_RESTORE="${HOME}/restore-me"
# rm -rf "${HOME}/.openclaw"
# cp -r "${PATH_RESTORE}" "${HOME}/.openclaw"
# apt install -y unzip
# (
#     cd "${HOME}/.openclaw/workspace/" || exit
#     unzip .git.zip -d .
#     rm .git.zip
# )
# openclaw gateway install
