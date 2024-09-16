lint:
    poetry run ruff check .
    poetry run ruff format . --diff
    poetry run pyright

format:
    poetry run ruff format .