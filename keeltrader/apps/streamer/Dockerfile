FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY streamer/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy streamer + shared engine types + package init
COPY __init__.py /app/apps/__init__.py
COPY streamer/ /app/apps/streamer/
COPY engine/__init__.py /app/apps/engine/__init__.py
COPY engine/event_types.py /app/apps/engine/event_types.py
COPY engine/event_bus.py /app/apps/engine/event_bus.py

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "apps.streamer.runner"]
