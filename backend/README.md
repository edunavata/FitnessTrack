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
