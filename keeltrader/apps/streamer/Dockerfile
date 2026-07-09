FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

COPY streamer/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r /tmp/requirements.txt

RUN useradd -m -u 1000 appuser && mkdir -p /app/apps/engine

# Legacy standalone image. Current Compose runs the active worker from keeltrader-api.
# Copy streamer + shared engine types + exchange adapter + package init.
COPY --chown=appuser:appuser __init__.py /app/apps/__init__.py
COPY --chown=appuser:appuser streamer/ /app/apps/streamer/
COPY --chown=appuser:appuser exchange/ /app/apps/exchange/
COPY --chown=appuser:appuser engine/__init__.py /app/apps/engine/__init__.py
COPY --chown=appuser:appuser engine/event_types.py /app/apps/engine/event_types.py
COPY --chown=appuser:appuser engine/event_bus.py /app/apps/engine/event_bus.py

USER appuser

CMD ["python", "-m", "apps.streamer.runner"]
