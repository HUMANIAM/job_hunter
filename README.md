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

Fetch jobs for the default source (`sioux`) and write only the final per-job match artifacts:

```bash
.venv/bin/python fetch_jobs.py
```

Fetch a specific source:

```bash
.venv/bin/python fetch_jobs.py --company sioux
```

Write all optional debug artifacts as well:

```bash
.venv/bin/python fetch_jobs.py \
  --company sioux \
  --write-raw \
  --write-evaluated \
  --write-validation
```

### CLI Options

- `--company <slug>`: source/company slug to fetch. Defaults to `sioux`.
- `--write-raw`: write per-job raw collected job artifacts.
- `--write-evaluated`: write per-job evaluated job artifacts with keep/skip metadata.
- `--write-validation`: write the collection validation artifact.

## Output Files

All generated files are written under `data/job_profiles/<company>/`.

Default run:

- `match/<job_title>__<url_hash>.json`: the final merged job payload for jobs that passed the evaluator.

Optional files:

- `raw/<job_title>__<url_hash>.json`: final merged job payload written as soon as extraction completes for a job.
- `evaluated/<job_title>__<url_hash>.json`: the same job payload plus keep/skip evaluation metadata, written immediately after ranking.
- `jobs_<company>_validation.json`: collection validation report from the adapter.

## Repository Policy

Local artifacts under `data/` are not tracked as source files.

The repository should track source code, tests, and project metadata, while keeping local environment state and generated data out of version control.
