FROM python:3.11-slim

# --- Env hygiene ---------------------------------------------------------
# PYTHONDONTWRITEBYTECODE: don't leave .pyc files inside the container
# PYTHONUNBUFFERED:        stream stdout immediately (critical for logs)
# PIP_NO_CACHE_DIR:        don't bloat the image with pip's download cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# --- System packages -----------------------------------------------------
# build-essential is needed by a few transitive deps (chroma's onnxruntime,
# tokenizers). curl is for healthchecks later. Apt cache removed to shrink image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- Python deps ---------------------------------------------------------
# We COPY requirements.txt FIRST, then RUN pip install, THEN copy source.
# Why the order matters: Docker caches each layer. As long as requirements.txt
# doesn't change, `docker build` skips pip install entirely on rebuilds.
# If we copied all source first, ANY code edit would re-trigger pip install.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# --- App source ----------------------------------------------------------
COPY app ./app

# --- Chroma volume mount point -------------------------------------------
# Create the dir BEFORE creating the non-root user, and chown it.
# When Docker mounts a named volume here for the first time, it copies
# this directory's ownership into the volume → appuser can write to it.
# Skip this and you get "Permission denied" the moment Chroma persists.
RUN mkdir -p /app/.chroma

# --- Non-root user (best practice) ---------------------------------------
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Default command; docker compose can override it.
CMD ["python", "-m", "app.main"]