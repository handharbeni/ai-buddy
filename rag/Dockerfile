FROM python:3.11-slim

WORKDIR /app

# System deps for sentence-transformers (torch) and pdf/docx parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model (saves runtime + ensures offline)
ENV HF_HOME=/app/.cache/hf
ENV TRANSFORMERS_CACHE=/app/.cache/hf
ARG EMBEDDING_MODEL=BAAI/bge-m3
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')" || \
    echo "WARNING: could not pre-download ${EMBEDDING_MODEL}; will download on first use"

# App code
COPY app/ /app/app/

# Non-root user
RUN useradd -m -u 1000 ragsvc && chown -R ragsvc:ragsvc /app
USER ragsvc

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
