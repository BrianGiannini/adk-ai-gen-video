FROM python:3.13-slim

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml ./
COPY uv.lock* ./

# Install Python dependencies WITHOUT creating a virtual environment
# This is key: use --no-cache and ensure we're using system Python
RUN uv sync --no-dev --no-cache

# Copy application code
COPY . .

# Expose port for the application
EXPOSE 8080

# Use uv run - it's faster and handles the environment correctly
CMD ["uv", "run", "--no-dev", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]