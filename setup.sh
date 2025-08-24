cd backend

# Directorios
mkdir -p app/api/v1 app/core app/models

# Archivos Python (módulos)
touch app/api/v1/__init__.py app/core/{__init__.py,config.py,database.py,logger.py} \
      app/models/{__init__.py,user.py} app/{__init__.py,factory.py} wsgi.py

# Requisitos y README
cat > requirements.txt <<'EOF'
flask==3.0.3
flask-cors==4.0.0
flask-sqlalchemy==3.1.1
Flask-Migrate==4.0.7
psycopg2==2.9.9
python-dotenv==1.0.1
EOF

cat > README.md <<'EOF'
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
EOF
