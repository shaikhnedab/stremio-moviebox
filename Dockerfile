# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock ./
COPY server/ ./server/
COPY streaming/ ./streaming/
COPY moviebox/ ./moviebox/
COPY web/ ./web/
COPY assets/ ./assets/
RUN uv sync --frozen --no-dev

# Ensure the appuser owns the directory
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Healthcheck to verify the server is running
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/manifest.json || exit 1

# Start the Stremio Addon Server
CMD ["uv", "run", "python", "-m", "server.main"]
