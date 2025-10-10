# `public`

## Scripts

### `generate-deploy-key.py`

```console
_file=$(mktemp) && wget -qO "$_file" https://raw.githubusercontent.com/queensberry-research/public/refs/heads/master/src/generate-deploy-key.py && python3 "$_file"
```
