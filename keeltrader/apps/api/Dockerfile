FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install API requirements first for caching
COPY apps/api/requirements.txt /app/requirements-api.txt
RUN pip install --no-cache-dir -r /app/requirements-api.txt

# Install Agent Matrix dependencies (pydantic-ai, ccxt, numpy, etc.)
# These are optional — if not present the agent routes degrade gracefully
RUN pip install --no-cache-dir \
    pydantic-ai>=0.1.0 \
    ccxt>=4.0.0 \
    numpy>=1.24.0 \
    redis>=5.0.0 2>/dev/null || true

# Copy all apps code (context = repo root)
COPY apps/ /app/apps/

# Copy Alembic config and migrations for database schema management
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/

# Symlink API code to /app for backward compatibility (existing imports use bare module names)
RUN for item in /app/apps/api/*; do \
      base=$(basename "$item"); \
      [ "$base" = "Dockerfile" ] && continue; \
      [ "$base" = "__pycache__" ] && continue; \
      ln -sf "$item" "/app/$base"; \
    done

# Fix Windows line endings in shell scripts
RUN find /app -name "*.sh" -exec sed -i 's/\r$//' {} \;

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
