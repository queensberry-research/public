ARG DEBIAN_VERSION
ARG PYTHON_VERSION
ARG PACKAGE_NAME
ARG PACKAGE_HAS_SCRIPTS

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-${DEBIAN_VERSION}-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PRERELEASE='disallow'
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=pyproject.toml,target=pyproject.toml --mount=type=bind,source=uv.lock,target=uv.lock --mount=type=bind,source=pyproject.toml,target=pyproject.toml --mount=type=bind,source=uv.lock,target=uv.lock --mount=type=bind,source=uv.lock,target=uv.lock uv sync --locked --no-install-project --no-dev

COPY src/${PACKAGE_NAME} /app/src/${PACKAGE_NAME}
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$PACKAGE_HAS_SCRIPTS" = "1" ]; then \
      uv sync --extra scripts --no-dev --locked; \
    else \
      uv sync --no-dev --locked; \
    fi

###############################################################################

ARG DEBIAN_VERSION
ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

CMD ["cli"]
