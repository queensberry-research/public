# `public`

## Installation

```console
rm -f /etc/apt/sources.list.d/{ceph,pve-enterprise}.sources && { command -v curl >/dev/null 2>&1 || { apt -y update && apt -y install curl; }; } && curl -fsLS https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/install.py | python3 -
```
