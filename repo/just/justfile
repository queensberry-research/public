set dotenv-load := true
set positional-arguments := true

@clean:
  git clean -fdx
  uv sync

cli *args:
  #!/usr/bin/env sh
  name=$(yq -p toml -o json '.' pyproject.toml | jq -r '.project.scripts | keys[]? | select(test("-cli$"))')
  if [ -n "${name}" ]; then
    "${name}" "$@"
  else
    echo "Project has no '*-cli' executable"
  fi

@plo:
  UV_INDEX=qrt=http://pypi uv pip list --outdated
