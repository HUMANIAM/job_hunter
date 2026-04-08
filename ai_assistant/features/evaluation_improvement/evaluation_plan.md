# Eligibility-First Ranking Refactor

## Summary
- Replace the current average-only ranking with a 3-stage flow:
  1. candidate must-have checks from `candidate_constraints`
  2. job must-have checks from extracted job constraints
  3. weighted feature ranking for surviving jobs
- Keep hard blockers out of the score model so failed must-haves no longer survive with diluted averages.

## Implementation Changes
- Reuse `candidate_constraints` as the candidate-side hard gate.
  - Treat `preferred_locations` and `preferred_workplace_types` as hard filters when populated.
  - Treat `excluded_locations`, `excluded_workplace_types`, `requires_visa_sponsorship`, and `avoid_export_control_roles` as hard blockers.
  - Treat unknown candidate eligibility for a hard legal/job constraint as a mismatch.
- Add `job_constraints` to the Sioux job model and schema.
  - Populate it from existing extracted job data: all `required` skills/languages/protocols/standards/domains, required years-experience, seniority, and legal restrictions.
  - Keep the original feature arrays and fields for score-phase matching and artifact explainability.
- Refactor ranking evaluation to return staged results.
  - Add `status`, `decision_stage`, and `rejection_reasons`.
  - Use `score=0.0` with zeroed bucket scores when ranking is skipped due to a hard-filter failure.
  - Keep `missing_features` for score-phase gaps only.
- Update the ranking service and CLI/reporting flow.
  - Always write the ranking artifact.
  - Write `match` artifacts for successful ranking-stage matches.
  - Add `data/job_profiles/<company>/mismatch` artifacts for candidate/job must-have failures and score-below-threshold outcomes.

## Verification
- Add evaluator tests for candidate-side hard filters, job-side hard filters, legal unknown handling, and ranking-stage threshold mismatches.
- Add schema/parser tests for `job_constraints`.
- Add writer and CLI tests for `mismatch` artifacts and the extended ranking payload.
- Run focused unit tests covering ranking, writer, schema, and fetch-job flow.

## Defaults
- No scraping/collection changes; filtering starts after the job has been parsed.
- Candidate-side must-haves come only from `candidate_constraints`; no new candidate schema section is introduced.
- Degree/education matching stays out of scope because the candidate profile has no comparable structured field.
