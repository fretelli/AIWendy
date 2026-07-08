FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

COPY streamer/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r /tmp/requirements.txt

# Legacy standalone image. Current Compose runs the active worker from keeltrader-api.
# Copy streamer + shared engine types + exchange adapter + package init.
COPY __init__.py /app/apps/__init__.py
COPY streamer/ /app/apps/streamer/
COPY exchange/ /app/apps/exchange/
COPY engine/__init__.py /app/apps/engine/__init__.py
COPY engine/event_types.py /app/apps/engine/event_types.py
COPY engine/event_bus.py /app/apps/engine/event_bus.py

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "apps.streamer.runner"]
