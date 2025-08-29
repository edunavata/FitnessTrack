# 1) Crear venv e instalar dependencias
source .venv/bin/activate
pip install -r requirements.txt

# 2) Exportar variables (puedes usar .env en la raíz; python-dotenv lo carga solo)
export FLASK_APP=wsgi:app
export FLASK_DEBUG=1
# Opcional: DATABASE_URL si quieres Postgres ya
# export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/fitdb

# 3) Inicializar Alembic/Flask-Migrate
flask db init
flask db migrate -m "init"
flask db upgrade

# 4) Levantar
flask run -p 8080
# Prueba en el navegador:
#   http://localhost:8080/api/v1/healthz
#   http://localhost:8080/api/v1/readiness
