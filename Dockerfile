FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8052

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY start.sh .
COPY analise_temporal ./analise_temporal
COPY assets ./assets
COPY static ./static
COPY templates ./templates
COPY saida/consolidado ./saida/consolidado

EXPOSE 8052

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail "http://localhost:${PORT}/healthz" || exit 1

CMD ["bash", "start.sh"]
