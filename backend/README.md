# Backend (Flask API)

## Quickstart (local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=wsgi:app
export FLASK_DEBUG=1
flask db init
flask db migrate -m "init"
flask db upgrade
flask run -p 8080
Variables de entorno importantes (ver .env.example en raíz):

ENV=development

SECRET_KEY=CHANGE_ME

DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/fitdb

Si no se define DATABASE_URL, se usará SQLite sqlite:///./dev.db

bash
Copiar
Editar

## Health
- `GET /api/v1/healthz`
- `GET /api/v1/readiness`

## Seeding
Use the Flask CLI after exporting `FLASK_APP=wsgi:app`:

```bash
flask seed run
```

The command is idempotent and can be run repeatedly to ensure the development database contains reference data. To reset the schema (development/testing only) run:

```bash
flask seed fresh --yes
```

`seed fresh` drops and recreates all tables before seeding; omit `--yes` to receive an interactive confirmation prompt.
