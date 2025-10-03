# FitnessTrack Backend

## Overview
- Flask-based REST API providing the FitnessTrack application's core services.
- Structured via the application factory pattern with environment-specific configuration.
- Includes CLI helpers for database migrations and deterministic development seeding.

## Quickstart
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure Flask entrypoint and enable debug for local development:
   ```bash
   export FLASK_APP=wsgi:app
   export FLASK_DEBUG=1
   export APP_ENV=development
   ```
4. Apply database migrations:
   ```bash
   flask db init      # only the first time
   flask db migrate -m "init"
   flask db upgrade
   ```
5. Start the development server:
   ```bash
   flask run -p 8080
   ```

## Environment Variables
| Variable       | Purpose                                   | Default                         |
| -------------- | ----------------------------------------- | ------------------------------- |
| `APP_ENV`      | Selects config class (`development`, `testing`, `production`). | `development` |
| `FLASK_APP`    | Flask entrypoint                          | `wsgi:app`                      |
| `FLASK_DEBUG`  | Enables debug mode                        | `0`                             |
| `SECRET_KEY`   | Flask session secret                      | `CHANGE_ME`                     |
| `JWT_SECRET_KEY` | JWT signing secret                     | `CHANGE_ME_JWT`                 |
| `DATABASE_URL` | SQLAlchemy connection string              | `sqlite:///./dev.db`            |

Refer to `.env.example` at the project root for additional options. Define the variables in your shell or a `.env` file before running the CLI.

## Database Migrations
- `flask db migrate -m "message"` generates migration scripts.
- `flask db upgrade` applies migrations.
- `flask db downgrade` rolls back the last migration.

## Seeding
The project ships with idempotent seeders exposed through the Flask CLI.

```bash
flask seed run
```

### Performing a Fresh Seed
`fresh` drops all tables, recreates the schema, and then runs the standard seeders. For safety, this command is blocked in production-like environments. Ensure the following before running it:

- `APP_ENV` is **not** `production` (e.g. set `export APP_ENV=development`).
- If you rely on Flask's legacy `ENV` variable, it must not resolve to production without `FLASK_DEBUG` or `TESTING` enabled.

Then execute:

```bash
flask seed fresh --yes
```

Omit `--yes` to receive a confirmation prompt. The command automatically drops the schema, recreates it, and prints a per-table summary of created vs. existing records.

## Health Checks
- `GET /api/v1/healthz`
- `GET /api/v1/readiness`

These endpoints are useful for container orchestration and uptime monitoring.

## Troubleshooting
- "`flask seed fresh` is restricted" &rarr; verify `APP_ENV`/`ENV` are set to a development or testing profile and `FLASK_DEBUG=1` when working locally.
- `ModuleNotFoundError` on app imports &rarr; ensure you've activated the virtual environment before invoking the CLI.
