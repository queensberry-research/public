# `public`

## Scripts

### `generate-deploy-key`

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/generate-deploy-key | bash -s -- KEY_NAME HOST_NAME
```

### `reboot-proxmox`

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/reboot-proxmox | sh
```

### `setup-venv`

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/setup-venv | sh
```

### `setup-infra`

```console
wget -qO- https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/setup-infra.py | python3.11 -
```
