# Test suite

This directory contains the pytest-based tests for the FitnessTrack API.

## Running tests

```bash
make test  # or simply: pytest
```

Coverage is enforced at 90%. To override the threshold (e.g., in CI) use
``PYTEST_ADDOPTS="--cov-fail-under=80"``.

## Fixtures

- ``app`` – Flask application created with the testing config.
- ``session`` – transactional SQLAlchemy session rolled back after each test.
- ``client`` – Flask test client.
- ``user`` / ``auth_token`` / ``auth_header`` – helpers for authenticated requests.
- ``freeze_time`` – factory for deterministic timestamps using *freezegun*.

Factories live in ``tests/factories`` and helpers in ``tests/helpers``.

## Adding new factories

Create a new module in ``tests/factories/`` inheriting from
``SQLAlchemyFactory`` and set ``sqlalchemy_session = db.session``.

## Adding endpoint tests

Place files under ``tests/integration/`` named ``test_<resource>.py``.
Follow the Arrange–Act–Assert pattern and prefer parametrization for
variants.

## Parallel execution

The setup works with ``pytest-xdist``. Each worker uses its own database
transaction; avoid global state.

## Continuous Integration

If using GitHub Actions, a minimal workflow could look like:

```yaml
# .github/workflows/tests.yml
# name: tests
# on: [push, pull_request]
# jobs:
#   tests:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - uses: actions/setup-python@v5
#         with:
#           python-version: '3.12'
#       - run: pip install -r backend/requirements.txt
#       - run: pip install -r requirements-dev.txt  # if present
#       - run: pytest
```

