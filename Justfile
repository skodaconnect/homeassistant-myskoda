lint:
    poetry run ruff check .
    poetry run ruff format . --dif
    poetry run mypy .

