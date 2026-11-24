FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCPI_DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --system --uid 10001 mcpi && mkdir -p /data && chown mcpi /data
USER mcpi

VOLUME ["/data"]
EXPOSE 5555

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:5555/healthz', timeout=4)" || exit 1

CMD ["python", "app.py"]
