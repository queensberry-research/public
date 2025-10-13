# `public`

## Scripts

### `install.py`

```console
command -v curl >/dev/null 2>&1 || { if [ "$(id -u)" -eq 0 ]; then apt -y install curl; else sudo apt -y install curl; fi; }; curl -fsLS https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/public/install.py | python3 - init
```

### `generate-deploy-key.py`

```console
_file=$(mktemp) && wget -qO "$_file" https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/generate-deploy-key.py && python3 "$_file"
```
