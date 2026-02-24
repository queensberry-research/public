# `public`

Public configs

## Installation

### Public

```console
if ! command -v curl >/dev/null 2>&1; then
    if [ "$(id -u)" = 0 ]; then
        apt-get update
        apt-get install -y curl
    else
        sudo apt-get update
        sudo apt-get install -y curl
    fi
fi
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/scripts/remote.sh | sh
```

### OpenClaw

```console
if ! command -v curl >/dev/null 2>&1; then
    if [ "$(id -u)" = 0 ]; then
        apt-get update
        apt-get install -y curl
    else
        sudo apt-get update
        sudo apt-get install -y curl
    fi
fi
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/scripts/openclaw.sh | sh
```
