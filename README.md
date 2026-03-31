# job_hunter

`job_hunter` is a standalone Python project for automating job discovery across target consultancy clients.

The long-term goal is to fetch published vacancies from selected clients, extract structured job data, and rank jobs against a given CV and target client profile so the search process becomes repeatable and easier to refine.

## Current State

The project is currently in active experimentation with Sioux vacancies. The scraper framework is intended to expand to additional clients such as ASML, Canon, Philips, and others over time.

Today the project already includes:
- a Playwright-based vacancy scraper
- structured raw and evaluated JSON outputs
- a collection validation step that compares facet-based collection with unfiltered pagination collection
- title and description based relevance filtering

## Local Development

This project uses the local virtual environment that already exists in the repository root.

Run tests:

```bash
.venv/bin/python -m unittest test_fetch_jobs.py
```

Run a syntax check:

```bash
.venv/bin/python -m py_compile fetch_jobs.py
```

Run the scraper:

```bash
.venv/bin/python fetch_jobs.py
```

## Repository Policy

Generated vacancy outputs under `vacancies/` are local artifacts and are not tracked as source files.

The repository should track source code, tests, and project metadata, while keeping local environment state and generated data out of version control.
