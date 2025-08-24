#!/usr/bin/env bash
set -euo pipefail

# Export Flask app para comandos CLI
export FLASK_APP="wsgi:app"

# Espera opcional a DB (simple y suficiente en compose)
if [[ -n "${WAIT_FOR_DB:-1}" ]]; then
  echo "Waiting for database at ${DATABASE_URL:-sqlite}..."
  # Pequeño retry loop para Postgres
  for i in {1..30}; do
    python - <<'PY'
import os, sys
url=os.getenv("DATABASE_URL","")
if url.startswith("postgres"):
    import psycopg2, urllib.parse
    from psycopg2 import OperationalError
    try:
        # Usa la cadena tal cual (psycopg2 acepta URI)
        conn=psycopg2.connect(url)
        conn.close()
        sys.exit(0)
    except OperationalError:
        sys.exit(1)
else:
    sys.exit(0)
PY
    ok=$?
    [[ $ok -eq 0 ]] && break || sleep 1
    echo "  retrying DB..."
  done
fi

# Migraciones automáticas (idempotentes). Desactiva con AUTO_MIGRATE=0
if [[ "${AUTO_MIGRATE:-1}" == "1" ]]; then
  echo "Running database migrations..."
  flask db upgrade || { echo "Migrations failed"; exit 1; }
fi

# Lanza Gunicorn
exec gunicorn -c gunicorn.conf.py "wsgi:app"
