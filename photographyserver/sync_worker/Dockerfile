FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy workspace configuration from homeserver root
COPY pyproject.toml uv.lock ./

# Copy source code in the same structure as workspace expects
COPY photographyserver ./photographyserver

# Install dependencies
RUN uv sync --frozen

# Create photos directory
RUN mkdir -p /app/photos

# Expose health check port
EXPOSE 8001

# Run the sync worker
CMD ["uv", "run", "src/pgs_sync/run.py"]