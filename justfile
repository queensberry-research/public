set dotenv-load := true
set positional-arguments := true

@install *args:
  python3 -m public.install "$@"
