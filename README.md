# `public`

## Scripts

### `backup-truenas`

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/backup-truenas | sh
```

### `generate-deploy-key`

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/generate-deploy-key | bash -s -- KEY_NAME HOST_NAME
```

### `purge-packages` (⚠️ - runs `sudo`)

```console
curl -fsSL https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/purge-packages | sudo python3
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
