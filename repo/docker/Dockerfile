ARG DEBIAN_VERSION=''
ARG PYTHON_VERSION=''

###############################################################################
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-${DEBIAN_VERSION}-slim AS builder
###############################################################################

ARG DEBIAN_VERSION=''
ARG PYTHON_VERSION=''
ARG PACKAGE_NAME_UNDERSCORE=''
ARG PACKAGE_HAS_SCRIPTS=0
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE='copy'
ENV UV_PRERELEASE='disallow'
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project --no-dev

COPY src/${PACKAGE_NAME_UNDERSCORE} /app/src/${PACKAGE_NAME_UNDERSCORE}
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$PACKAGE_HAS_SCRIPTS" = "1" ]; then \
      uv sync --extra scripts --no-dev --locked; \
    else \
      uv sync --no-dev --locked; \
    fi

###############################################################################
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}
###############################################################################

RUN echo '' \
    && apt-get update \
    && apt-get install -y --no-install-recommends age \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && echo ''

COPY --from=builder /app /app

COPY --from=ghcr.io/getsops/sops:v3.11.0 /usr/local/bin/sops /usr/local/bin/
# https://github.com/getsops/sops/pkgs/container/sops

ENV PATH=/app/.venv/bin:${PATH}
ENV PATH=/root/.local/bin:${PATH}

WORKDIR /app

CMD ["cli"]
