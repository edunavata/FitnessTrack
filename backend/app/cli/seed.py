"""Flask CLI commands for deterministic development database seeding."""

from __future__ import annotations

import logging

import click
from flask import current_app
from flask.cli import with_appcontext

from app.core.extensions import db
from app.seeds import seed_data

LOGGER = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    """Raise logging verbosity for seed modules when requested."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger("app.seeds").setLevel(level)
    logging.getLogger(seed_data.__name__).setLevel(level)
    LOGGER.setLevel(level)


def _echo_summary(summary: dict[str, dict[str, int]]) -> None:
    """Pretty-print a tabular summary of seed results."""
    click.echo("Seed summary:")
    if not summary:
        click.echo("  (no changes)")
        return
    width = max(len(name) for name in summary)
    for table, counters in sorted(summary.items()):
        created = counters.get("created", 0)
        existing = counters.get("existing", 0)
        click.echo(f"  {table.ljust(width)}  created={created:>2}  existing={existing:>2}")


def _ensure_non_production() -> None:
    """Abort destructive commands when running in production."""
    config = current_app.config
    env = str(config.get("ENV", "production")).lower()
    app_env = str(config.get("APP_ENV", "")).lower()
    is_debug = bool(config.get("DEBUG"))
    is_testing = bool(config.get("TESTING"))
    if app_env == "production" or (env == "production" and not is_debug and not is_testing):
        raise click.UsageError(
            "The 'flask seed fresh' command is restricted to non-production environments."
        )


@click.group("seed")
@click.option("--verbose", is_flag=True, help="Enable verbose logging for seeding.")
@click.pass_context
def seed_cli(ctx: click.Context, verbose: bool) -> None:
    """Collection of database seeding commands."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _configure_logging(verbose)


@seed_cli.command("run")
@click.pass_context
@with_appcontext
def run_command(ctx: click.Context) -> None:
    """Populate the database with idempotent development fixtures."""
    verbose = bool(ctx.obj.get("verbose", False))
    try:
        summary = seed_data.run_all(db, verbose=verbose)
    except Exception as exc:  # pragma: no cover - CLI safeguard
        db.session.rollback()
        raise click.ClickException(f"Seeding failed: {exc}") from exc
    _echo_summary(summary)


@seed_cli.command("fresh")
@click.option("--yes", is_flag=True, help="Skip the destructive confirmation prompt.")
@click.pass_context
@with_appcontext
def fresh_command(ctx: click.Context, yes: bool) -> None:
    """Drop all tables, recreate the schema, and seed development data."""
    _ensure_non_production()
    if not yes:
        click.confirm(
            "This will DROP all application tables and recreate them. Continue?",
            abort=True,
        )
    verbose = bool(ctx.obj.get("verbose", False))
    LOGGER.info("Dropping database schema...")
    db.session.remove()
    db.drop_all()
    LOGGER.info("Recreating database schema...")
    db.create_all()
    try:
        summary = seed_data.run_all(db, verbose=verbose)
    except Exception as exc:  # pragma: no cover - CLI safeguard
        db.session.rollback()
        raise click.ClickException(f"Fresh seed failed: {exc}") from exc
    _echo_summary(summary)
