FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

COPY engine/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r /tmp/requirements.txt

# Legacy standalone image. Current Compose runs agent-engine from keeltrader-api.
# Copy all apps modules (engine needs agents, tools, memory, execution).
COPY . /app/apps/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "apps.engine.runner"]
