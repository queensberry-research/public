# `public`

## Scripts

### `generate-deploy-key.py`

```console
_file=$(mktemp) && wget -qO "$_file" https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/generate-deploy-key.py && python3 "$_file"
```

### `reboot-proxmox`

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/reboot-proxmox | sh
```

### `setup-venv`

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/setup-venv | sh
```

### `setup-infra.py`

```console
wget -qO- https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/setup-infra.py | python3 -
```
