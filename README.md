# FitnessTrack

A full-stack fitness workout tracking application built to consolidate the skills honed during my internship at **EDP Renewables**. FitnessTrack streamlines tracking workouts, exercises, and routines while providing a production-ready architecture for experimentation and learning.

## Badges

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)
![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?logo=docker&logoColor=white)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-lightgrey?logo=github)

## Features

- **Authentication & Authorization** – Secure access to protected API routes using token-based auth.
- **Healthcheck** – Lightweight service endpoints to validate application and database availability.
- **User Management** – CRUD operations for registering, updating, and deactivating users.
- **Workout Tracking** – Organize workouts with session metadata, logs, and progress tracking.
- **Exercise Library** – Maintain catalogues of exercises with categories, muscles, and equipment metadata.
- **Routine Builder** – Assemble reusable templates that combine workouts and exercises for recurring plans.
- **Error Handling & Logging** – Structured error responses with centralized logging for troubleshooting.

## Tech Stack

- **Backend:** Flask, SQLAlchemy ORM, Alembic migrations
- **Frontend:** React
- **Database:** Configurable via SQLAlchemy (SQLite for local dev, PostgreSQL-ready for production)
- **Web Server:** Nginx reverse proxy
- **Containerization:** Docker, Docker Compose
- **Testing & Quality:** pytest, bandit, mypy

## Project Structure

```text
.
├── backend/                  # Flask application code and configuration
│   ├── app/
│   ├── entrypoint.sh
│   ├── gunicorn.conf.py
│   ├── migrations/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── setup.sh
│   ├── tests/
│   └── wsgi.py
├── frontend/                 # React frontend source
├── deploy/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   └── nginx.Dockerfile
│   └── nginx/default.conf
├── tests/                    # Cross-cutting integration / e2e suites
├── compose.yaml              # Full-stack Docker Compose definition
├── bandit.yaml               # Security scanner configuration
├── mypy.ini                  # Static typing configuration
├── pyproject.toml            # Shared tooling configuration (ruff, pytest, etc.)
└── README.md
```

## Data Model Documentation

Review the [backend data model reference](backend/app/models/README.md) for a complete overview of every domain entity. The document includes detailed field descriptions and an accompanying Mermaid diagram that visualizes the relationships across the schema.

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/edunavata/FitnessTrack.git
   cd FitnessTrack
   ```
2. **Create and activate a virtual environment** (Python 3.11+ recommended)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. **Install backend dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```
4. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

## Running with Docker Compose

Spin up the full stack (backend, frontend, and Nginx proxy) using the root Compose file:

```bash
docker compose up --build
```

The command builds all images, applies migrations automatically, and starts every service. Visit the frontend URL exposed by Nginx (typically `http://localhost:8080`) to interact with the app.

## Running the Backend Only

Use the root Compose file to start only the API and its database dependencies:

```bash
docker compose up --build backend db
```

Alternatively, build and run the backend image directly without Compose:

```bash
docker build -f deploy/docker/backend.Dockerfile -t fitnesstrack-backend .
docker run --rm -p 8000:8000 --env-file .env fitnesstrack-backend
```

Adjust environment variables (database URL, logging, CORS origins) as needed for your workflow.

## Development Notes

- **Migrations:** Manage schema changes with Alembic via the Flask CLI.
  ```bash
  flask db migrate -m "Add new table"
  flask db upgrade
  ```
- **Testing:** Execute the pytest suites from the repository root or within `backend/tests` and `tests/`.
  ```bash
  pytest
  ```
- **Linting & Security:** Leverage Ruff (configured in `pyproject.toml`) and Bandit.
  ```bash
  ruff check .
  bandit -c bandit.yaml -r backend
  ```
- **Static Typing:** Ensure type coverage with mypy.
  ```bash
  mypy --config-file mypy.ini .
  ```

## Testing

FitnessTrack includes comprehensive automated coverage:

- **Unit tests:** Validate isolated components such as utilities, models, and services.
- **Integration tests:** Assert behavior across API routes, database interactions, and middleware.
- **End-to-end tests:** Exercise complete user workflows across the stack.

Install testing dependencies:
```bash
pip install -r backend/requirements-dev.txt
```

Run the entire suite with:

```bash
pytest
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository and create a feature branch.
2. Follow the existing code style and naming conventions.
3. Include tests and documentation updates where appropriate.
4. Submit a pull request describing your changes.

## License

This project is licensed under the [MIT License](LICENSE).

## Author & Acknowledgements

Developed by **Eduardo González Fernández**. Special thanks to the mentors and colleagues at **EDP Renewables** for guidance throughout the internship.
