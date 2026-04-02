# job_hunter

`job_hunter` is a standalone Python project for automating job discovery across target consultancy clients.

The long-term goal is to fetch published vacancies from selected clients, extract structured job data, and rank jobs against a given CV and target client profile so the search process becomes repeatable and easier to refine.

## Current State

The project is currently in active experimentation with Sioux vacancies. The scraper framework is intended to expand to additional clients such as ASML, Canon, Philips, and others over time.

Today the project already includes:
- a Playwright-based vacancy scraper
- per-job ranking results against a candidate profile
- optional raw, evaluated, and validation JSON artifacts
- a collection validation step that compares facet-based collection with unfiltered pagination collection

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
.venv/bin/python -m py_compile app/job_hunter.py
```

## Usage

Run the single project entrypoint:

```bash
.venv/bin/python app/job_hunter.py
```

Fetch a specific source:

```bash
.venv/bin/python app/job_hunter.py --company sioux
```

Use a specific candidate profile:

```bash
.venv/bin/python app/job_hunter.py \
  --company sioux \
  --candidate-profile data/candidate_profiles/Ibrahim_Saad_CV.json
```

Write all optional debug artifacts as well:

```bash
.venv/bin/python app/job_hunter.py \
  --company sioux \
  --write-raw \
  --write-evaluated \
  --write-validation
```

### CLI Options

- `--company <slug>`: source/company slug to fetch. Defaults to `sioux`.
- `--candidate-profile <path>`: candidate profile JSON used for ranking.
- `--write-raw`: write per-job raw collected job artifacts.
- `--write-evaluated`: write per-job evaluated job artifacts with embedded ranking metadata.
- `--write-validation`: write the collection validation artifact.

## Output Files

Ranking files are written under `data/rankings/`.

- `<candidate_id>_<job_id>.json`: one ranking result per extracted job.

Additional source artifacts are written under `data/job_profiles/<company>/`.

Optional files:

- `raw/<job_title>__<url_hash>.json`: final merged job payload written as soon as extraction completes for a job.
- `evaluated/<job_title>__<url_hash>.json`: the same job payload plus embedded ranking metadata, written immediately after ranking.
- `jobs_<company>_validation.json`: collection validation report from the adapter.

## Repository Policy

Local artifacts under `data/` are not tracked as source files.

The repository should track source code, tests, and project metadata, while keeping local environment state and generated data out of version control.
