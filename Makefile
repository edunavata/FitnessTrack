.PHONY: test lint

# Run test suite with coverage
test:
	pytest --cov

# Run linters (ruff and mypy)
lint:
	ruff backend/app tests
	mypy backend/app tests
