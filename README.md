# job_hunter

`job_hunter` is a standalone Python project for automating job discovery across target consultancy clients.

The long-term goal is to fetch published vacancies from selected clients, extract structured job data, and rank jobs against a given CV and target client profile so the search process becomes repeatable and easier to refine.

## Current State

The project is currently in active experimentation with Sioux vacancies. The scraper framework is intended to expand to additional clients such as ASML, Canon, Philips, and others over time.

Today the project already includes:
- a Playwright-based vacancy scraper
- candidate-profile reuse or extraction from a CV source file
- per-job evaluated job profiles and ranking results
- optional raw and validation JSON artifacts
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
.venv/bin/python -m app.job_hunter
```

Rerank existing job profile JSON files without refetching:

```bash
.venv/bin/python -m app.rerank_jobs
```

Fetch a specific source:

```bash
.venv/bin/python -m app.job_hunter --company sioux
```

Use a specific candidate profile:

```bash
.venv/bin/python -m app.job_hunter \
  --company sioux \
  --cv data/candidate_profiles/Ibrahim_Saad_CV.json
```

Build or refresh the candidate profile from a CV source file:

```bash
.venv/bin/python -m app.job_hunter \
  --company sioux \
  --cv data/candidate_profiles/Ibrahim_Saad_CV.md
```

Write all optional debug artifacts as well:

```bash
.venv/bin/python -m app.job_hunter \
  --company sioux \
  --write-raw \
  --write-evaluated \
  --write-validation
```

### CLI Options

- `--company <slug>`: source/company slug to fetch. Defaults to `sioux`.
- `--candidate-profile <path>` / `--cv <path>`: candidate profile JSON or CV source file used for ranking. Non-JSON inputs are extracted once and persisted under `data/candidate_profiles/`.
- evaluated job profiles are always written under `data/job_profiles/<company>/evaluated/`.
- `--write-raw`: also write per-job raw artifacts under `data/job_profiles/<company>/raw/`.
- `--write-evaluated`: deprecated compatibility flag; evaluated artifacts are already written by default.
- `--write-validation`: write the collection validation artifact.

### Rerank Existing Jobs

Rerank a single evaluated job JSON against a single candidate profile JSON:

```bash
.venv/bin/python -m app.rerank_jobs \
  --job-profile data/job_profiles/sioux/evaluated/example.json \
  --candidate-profile data/candidate_profiles/Ibrahim_Saad_CV.json
```

If no arguments are provided, the rerank command falls back to:

- `data/job_profiles/sioux/evaluated/*.json`
- `data/candidate_profiles/*.json`

## Output Files

Candidate profiles are written under `data/candidate_profiles/`.

- `<candidate_id>.json`: reusable extracted candidate profile.

Job profiles are written under `data/job_profiles/<company>/`.

- `evaluated/<job_title>__<url_hash>.json`: one evaluated job profile per extracted vacancy, written before ranking.

Ranking files are written under `data/job_profiles/<company>/rankings/`.

- `rankings/match/<candidate_id>_<job_id>.json`: one ranking result per matched job.
- `rankings/mismatch/<candidate_id>_<job_id>.json`: one ranking result per mismatched job.

Optional files:

- `raw/<job_title>__<url_hash>.json`: raw per-job artifact for debugging.
- `jobs_<company>_validation.json`: collection validation report from the adapter.

## Repository Policy

Local artifacts under `data/` are not tracked as source files.

The repository should track source code, tests, and project metadata, while keeping local environment state and generated data out of version control.
