# Sioux Base vs LLM Output Comparison

## Question

What changed between the baseline Sioux analysis output and the newer
LLM-enriched output?

## Compared Artifacts

- Baseline: `data/analysis/sioux_base/jobs_sioux.json`
- Current extraction-comparable output in this workspace:
  `data/analysis/sioux_no_skipping/jobs_sioux.json`

Why not compare against `data/analysis/sioux/jobs_sioux.json` directly?

- that file exists in the current workspace
- but it is already affected by evaluator hard filters
- it currently keeps only `4` jobs instead of the baseline `13`

For extraction quality comparison, `sioux_no_skipping` is the cleaner
like-for-like artifact because it preserves the same kept job set as the
baseline file.

## High-Level Summary

At the job-set level, nothing changed:

- `total_jobs`: `32` in both files
- `relevant_jobs`: `13` in both files
- stored job entries: `13` in both files
- added URLs: `0`
- removed URLs: `0`

So the kept set is identical. The differences are field-level changes inside
the same 13 job entries.

## Schema-Only Additions

The newer output adds these fields to every compared job:

- `evidence`
- `preferred_domains`
- `preferred_protocols`
- `preferred_standards`
- `required_domains`
- `required_protocols`
- `required_standards`
- `restrictions`
- `seniority_hint`

These additions are the main structural improvement of the LLM-enriched
version. They make downstream filtering and auditing much easier.

## Change Frequency

The most frequently changed fields are:

- `evidence`: `13/13`
- `preferred_domains`: `13/13`
- `preferred_protocols`: `13/13`
- `preferred_standards`: `13/13`
- `required_domains`: `13/13`
- `required_protocols`: `13/13`
- `required_skills`: `13/13`
- `required_standards`: `13/13`
- `restrictions`: `13/13`
- `seniority_hint`: `13/13`
- `experience_text`: `11/13`
- `preferred_skills`: `9/13`
- `required_languages`: `6/13`
- `preferred_languages`: `1/13`

## Likely Improvements

### 1. Skills Are More Normalized

The baseline file stores long requirement sentences in `required_skills`. The
newer output converts many of those into compact normalized tokens.

Example: `Embedded Software Designer`

- Baseline `required_skills` includes long phrases such as:
  `Knowledge of hardware and communication protocols (UART, SPI, CAN, I2C)`
- Newer `required_skills` becomes:
  `embedded c`, `c++`, `python`, `real-time systems`, `state machines`,
  `software design`, `software testing`

That is much better for matching, filtering, and deduplication.

### 2. Domains, Protocols, and Standards Are Now Explicit

The newer output extracts structured technical metadata that the baseline file
did not represent at all.

Example: `Embedded Software Designer`

- `required_domains`:
  `high-tech`, `semiconductor`, `analytical equipment`, `medical devices`
- `required_protocols`:
  `uart`, `spi`, `can`, `i2c`
- `required_standards`:
  `iec 61508`, `sil`, `misra`

This is useful for both hard filters and future ranking improvements.

### 3. Restrictions Are Explicitly Captured

The baseline file does not represent export-control or clearance constraints.
The newer output does.

Example:

- `restrictions`:
  `export control access requirement`

That is directly useful for the new hard-filter policy in
`ranking/evaluator.py`.

### 4. Evidence Makes the Extraction Auditable

The newer output stores supporting text snippets under `evidence`, which makes
it possible to inspect why the model assigned a skill, language, domain, or
restriction.

That is a strong improvement over implicit extraction with no traceability.

## Likely Regressions or Bugs

### 1. `experience_text` Became Too Broad

This is the clearest quality regression.

In the baseline file, `experience_text` is usually a focused experience phrase.
In the newer file, it often expands into a long pasted block that includes
unrelated requirements and benefits text.

Example: `Embedded Software Designer`

- Baseline:
  `5 year experience Hands-on experience in embedded C/C++ software development`
- Newer:
  a long block that also includes unrelated requirement lines and even
  compensation/benefit text

This weakens the field for downstream reasoning and display.

### 2. Human Languages and Programming Languages Were Mixed

Example: `Test Designer`

- Baseline `required_languages`: `[]`
- Newer `required_languages`: `python`, `c#`, `c++`

That is almost certainly incorrect. Those are programming languages, not human
languages. This is a schema/prompt/extraction boundary issue and should be
fixed before trusting `required_languages` for filtering.

### 3. Required vs Preferred Language Classification Shifted

Example: `Software Architect`

- Baseline `required_languages`:
  `English`, `Dutch`, `German`
- Newer `required_languages`:
  `english`, `dutch`
- Newer `preferred_languages`:
  `german`

The newer interpretation may actually be more correct because the source text
appears to say `German is a strong plus`, but this is still a behavior change
worth reviewing because it changes downstream filtering semantics.

### 4. Some Evidence Strings Show Encoding Noise

At least one restriction evidence string contains an odd control-like character
in the EAR citation text. That suggests the extraction pipeline should also
guard against malformed copied text in evidence payloads.

## Example Job Delta Summary

### Embedded Software Designer

Net effect:

- better normalized skills
- new structured protocols, standards, domains, restrictions, evidence
- worse `experience_text`

### Test Designer

Net effect:

- useful normalized skills and evidence
- clear regression in `required_languages`
- worse `experience_text`

### Software Architect

Net effect:

- more structured output and clearer preferred-language separation
- possible behavior shift for `german`
- worse `experience_text`

## Recommended Next Fixes

1. Tighten `experience_text` extraction so it captures only the explicit
   experience span, not a long surrounding block.
2. Enforce that `required_languages` and `preferred_languages` are human
   languages only.
3. Keep programming-language extraction exclusively in skills or in a separate
   schema field if needed later.
4. Add a regression test for `Test Designer` so `python`, `c#`, and `c++`
   cannot land in human-language fields again.
5. Normalize or sanitize evidence text before persisting it.
