FROM python:3.11-slim


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# --- App source ----------------------------------------------------------
COPY app ./app



# --- Non-root user  ---------------------------------------
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Default command; docker compose can override it.
CMD uvicorn app.api.server:app --host 0.0.0.0 --port ${PORT:-8000}