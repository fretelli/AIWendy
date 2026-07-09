FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

COPY engine/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r /tmp/requirements.txt

RUN useradd -m -u 1000 appuser && mkdir -p /app/apps

# Legacy standalone image. Current Compose runs agent-engine from keeltrader-api.
# Copy only the Python modules needed by the legacy event engine.
COPY --chown=appuser:appuser __init__.py /app/apps/__init__.py
COPY --chown=appuser:appuser agents/ /app/apps/agents/
COPY --chown=appuser:appuser engine/ /app/apps/engine/
COPY --chown=appuser:appuser exchange/ /app/apps/exchange/
COPY --chown=appuser:appuser execution/ /app/apps/execution/
COPY --chown=appuser:appuser memory/ /app/apps/memory/
COPY --chown=appuser:appuser tools/ /app/apps/tools/

USER appuser

CMD ["python", "-m", "apps.engine.runner"]
