# syntax=docker/dockerfile:1.7
# Use a Python 3.10 image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install the project's dependencies using the lockfile and settings
# This layer is cached as long as uv.lock and pyproject.toml don't change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the project source code
COPY . /app

# Install the project itself (if it's defined in pyproject.toml)
# This is separate to optimize caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run the FastAPI application in production mode
CMD ["uv", "run", "uvicorn", "main:app", "--ws-ping-interval=2400", "--ws-ping-timeout=60", "--host", "0.0.0.0", "--port", "8080"]
