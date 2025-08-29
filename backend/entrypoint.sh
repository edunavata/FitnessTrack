#!/usr/bin/env bash
set -euo pipefail

# Export Flask app para comandos CLI
export FLASK_APP="wsgi:app"

# Migraciones automáticas (idempotentes). Desactiva con AUTO_MIGRATE=0
if [[ "${AUTO_MIGRATE:-1}" == "1" ]]; then
  echo "Running database migrations..."
  flask db upgrade || { echo "Migrations failed"; exit 1; }
fi

# Lanza Gunicorn
exec gunicorn -c gunicorn.conf.py "wsgi:app"
