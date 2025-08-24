# Etapa base
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dependencias del sistema (runtime + build para psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias primero (mejor caché)
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia app
COPY backend/ /app/

# Usuario no root
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
