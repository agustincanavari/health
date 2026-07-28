# health

Personal health tools, managed with pyenv + Poetry. Each tool lives under
`health/scripts/` as a CLI command, wired up in the `Makefile`.

## Setup

```
pyenv install -s   # uses the version pinned in .python-version
make install        # poetry install
```

## Tools

### `dicom-to-pdf`

Joins a folder of DICOM files (e.g. an MRI/CT export) into a single shareable
PDF: a cover page with patient info and a series index, followed by a
contact-sheet page per series.

```
make dicom-to-pdf ARGS="'/path/to/dicom/folder' -o resumen.pdf"
```

Run `poetry run dicom-to-pdf --help` for all options (anonymization,
images-per-series, DPI, etc).

## Adding a new tool

1. Add `health/scripts/<tool>.py` with a `main()` entry point.
2. Put any reusable logic in a sibling package under `health/` (e.g.
   `health/dicom/`) so it can be shared across tools.
3. Register it in `pyproject.toml` under `[tool.poetry.scripts]`.
4. Add a Makefile target that calls `poetry run <tool>`.
5. Run `make install` to pick up the new script.
