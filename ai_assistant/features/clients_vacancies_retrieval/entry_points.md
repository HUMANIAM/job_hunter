# Parallel Entry-Point Research Instructions

## Summary

This file is the coordinator brief for a 4-way parallel research pass over the
203 unique companies in `docs/clean_data.xlsx`.

The work is split into 4 contiguous 1-based ranges:

- `start1_end51.md`
- `start52_end102.md`
- `start103_end153.md`
- `start154_end203.md`

One range is owned by the main agent, and the other three ranges are owned by
three subagents. Each agent writes only its own range file.

## Mission

Find one Netherlands vacancy retrieval entry point per company from
`docs/clean_data.xlsx`.

## Source List

- Use the deduplicated company list in `docs/clean_data.xlsx`.
- Treat company indexing as 1-based.
- Ignore the header row.
- Company 1 is the first company row after the header.

## Range Split

- Agent 1: indices `1-51`
- Agent 2: indices `52-102`
- Agent 3: indices `103-153`
- Agent 4: indices `154-203`

## Output Files

Each agent must write exactly one file in
`ai_assistant/features/clients_vacancies_retrieval/`:

- `start1_end51.md`
- `start52_end102.md`
- `start103_end153.md`
- `start154_end203.md`

## Ownership Rule

- Each agent may edit only its own range file.
- `entry_points.md` is the shared instruction file only.
- No agent should overwrite another agent's report file.

## Acceptance Rule For URLs

- Only official company-owned careers pages or company-branded ATS pages are
  allowed.
- Prefer Netherlands-specific vacancy pages first.
- If no NL-specific page exists, allow a company-owned careers search page only
  when NL filtering is clearly available there.
- Do not use job boards or aggregators.

## Explicitly Rejected Sources

Do not use third-party job boards or aggregators such as:

- LinkedIn
- Indeed
- Glassdoor
- YoungCapital
- Nationale Vacaturebank
- Manpower
- Randstad
- Similar third-party vacancy aggregators

## Legacy Or Acquired Brand Rule

A legacy company name may map to the current employer careers surface when
supported by live evidence.

Example:

`FEI Electron Optics -> Thermo Fisher Scientific Netherlands jobs`

## Research Method

- Search for official NL careers pages first.
- Then search for company ATS pages.
- Prefer retrieval-ready listing or search pages over generic employer-brand
  pages.
- Prefer NL-scoped pages over global careers homepages.

## Per-Company Recording Format

For verified entry points:

`Company: vacancy_url`

For unresolved companies:

`Company: not found`

`Reason: why no reliable official NL entry point was confirmed`

`Found: rejected candidate 1; rejected candidate 2; ...`

## Evidence Rule

Every accepted URL must come from live company or ATS evidence, not guessed URL
patterns.

## Completion Rule

Every company in the assigned range must appear exactly once in that range
file.

## Per-Agent Report Structure

Each `startX_endY.md` file must use this layout:

- Title line with the covered range.
- One flat list of company results in spreadsheet order for that range.
- Each result uses one of the two allowed shapes:

`Company: vacancy_url`

or

`Company: not found`

`Reason: ...`

`Found: ...`

No nested structure, no prose summary, and no skipped companies.

## Parallel Execution Plan

- Main agent prepares `entry_points.md` with the full shared instruction set.
- Main agent assigns the 4 fixed contiguous ranges above.
- Main agent keeps one range locally and spawns 3 subagents for the remaining
  3 ranges.
- Each subagent researches only its assigned range and writes only its own
  `startX_endY.md`.
- After all 4 range files are complete, the main agent reviews them for:
  official-source compliance, no missing companies, no duplicate coverage, and
  no third-party job-board URLs accepted by mistake.

## Test Plan

- Confirm `docs/clean_data.xlsx` contains 203 companies and that the 4 ranges
  cover `1-203` with no gaps or overlaps.
- Confirm each range file name matches the agreed pattern and range.
- Confirm each company in each assigned range appears exactly once.
- Confirm each accepted URL is official, company ATS, and NL-valid.
- Confirm each unresolved company includes both `Reason:` and `Found:`.

## Assumptions

- `docs/clean_data.xlsx` is already the correct deduplicated source list and
  does not need regeneration.
- File naming is 1-based and uses the `startX_endY.md` pattern.
- The only shared file is `entry_points.md`; all findings live in the 4 range
  files.
- Consolidation into a single final inventory is a later step, not part of
  this instruction-writing step.
