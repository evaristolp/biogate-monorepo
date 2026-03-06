# BioGate FastAPI backend — production image (WeasyPrint + system deps)
FROM python:3.12-slim-bookworm

WORKDIR /app

# WeasyPrint + python-magic system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    shared-mime-info \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Backend Python deps (repo root so scripts/ and backend/ are on path)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Optional: scripts deps if you run ingestion in this image (e.g. cron)
COPY scripts/requirements.txt scripts/requirements.txt
RUN pip install --no-cache-dir -r scripts/requirements.txt 2>/dev/null || true

# Application code (backend + scripts for fuzzy_match etc.)
COPY backend/ backend/
COPY scripts/ scripts/

# Run from repo root so "backend.main:app" and script imports work
WORKDIR /app
ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
