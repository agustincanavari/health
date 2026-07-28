.PHONY: install dicom-to-pdf test lint format

install:
	poetry install

dicom-to-pdf:
	poetry run dicom-to-pdf $(ARGS)

test:
	poetry run pytest

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
