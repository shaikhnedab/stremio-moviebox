FROM python:3.12-slim-bookworm

WORKDIR /app

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv directly into the system to handle the pyproject.toml
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv
ENV PATH="/uv/bin:$PATH"

# Copy dependency files and install them globally (--system)
COPY pyproject.toml uv.lock ./
RUN uv pip install --system -r pyproject.toml

# Copy the rest of the application files
COPY . /app
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "server.main"]