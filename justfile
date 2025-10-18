set dotenv-load := true
set positional-arguments := true

@install *args:
  PYTHONPATH=src python3 -m public.install "$@"
