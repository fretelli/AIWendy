FROM python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4

# Set working directory
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple/

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

# Copy and install API runtime requirements first for caching.
COPY apps/api/requirements-prod.txt /app/requirements-api.txt
RUN pip install --no-cache-dir --prefer-binary -r /app/requirements-api.txt

# Copy only API code into the API image.
COPY apps/api/ /app/apps/api/

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
