set dotenv-load := true
set positional-arguments := true

@install *args:
  python -m public.install "$@"
