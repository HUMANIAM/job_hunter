# job_hunter

`job_hunter` is a standalone Python project for automating job discovery across target consultancy clients.

The long-term goal is to fetch published vacancies from selected clients, extract structured job data, and rank jobs against a given CV and target client profile so the search process becomes repeatable and easier to refine.

## Current State

The project is currently in active experimentation with Sioux vacancies. The scraper framework is intended to expand to additional clients such as ASML, Canon, Philips, and others over time.

Today the project already includes:
- a Playwright-based vacancy scraper
- a final structured job output for the kept vacancies
- optional raw, evaluated, and validation JSON artifacts
- a collection validation step that compares facet-based collection with unfiltered pagination collection
- title and description based relevance filtering

## Local Development

This project uses the local virtual environment that already exists in the repository root.

Run unit tests:

```bash
.venv/bin/python -m pytest tests/unit
```

Run the full test suite:

```bash
.venv/bin/python -m pytest
```

Run a syntax check:

```bash
.venv/bin/python -m py_compile fetch_jobs.py
```

## Usage

Fetch jobs for the default source (`sioux`) and write only the final kept-jobs file:

```bash
.venv/bin/python fetch_jobs.py
```

Fetch a specific source:

```bash
.venv/bin/python fetch_jobs.py --company sioux
```

Write all optional artifacts as well:

```bash
.venv/bin/python fetch_jobs.py \
  --company sioux \
  --write-raw \
  --write-evaluated \
  --write-validation
```

### CLI Options

- `--company <slug>`: source/company slug to fetch. Defaults to `sioux`.
- `--write-raw`: write the raw collected jobs artifact.
- `--write-evaluated`: write the evaluated jobs artifact with keep/skip metadata.
- `--write-validation`: write the collection validation artifact.

## Output Files

All generated files are written under `data/analysis/<company>/`.

Default run:

- `jobs_<company>.json`: final kept jobs after relevance filtering. This file is always written.

Optional files:

- `jobs_<company>_raw.json`: all fetched job payloads before ranking.
- `jobs_<company>_evaluated.json`: fetched jobs plus keep/skip decision metadata.
- `jobs_<company>_validation.json`: collection validation report from the adapter.

## Repository Policy

Generated vacancy outputs under `data/analysis/sioux/` are local artifacts and are not tracked as source files.

The repository should track source code, tests, and project metadata, while keeping local environment state and generated data out of version control.
