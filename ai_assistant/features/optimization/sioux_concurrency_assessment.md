# Sioux Concurrency Assessment

## Question

Can the Sioux job collection and parsing flow use system threading so that each
facet runs independently and jobs are processed only once through shared memory?

## Short Answer

Yes, concurrency can help here because the workload is mostly I/O-bound
(Playwright navigation plus one LLM API call per job). But the exact design
"each facet thread claims a job URL and immediately parses it" is not the safe
shape for the current pipeline.

The main reason is that the same vacancy URL can appear under multiple facets,
and the collector currently uses that to build `discipline_map`. If the first
thread that sees a URL immediately parses it, that job can be processed before
other facets attach their disciplines to the same URL.

## Current Runtime Graph

```text
CLI
-> source registry
-> Sioux adapter
-> facet traversal graph
-> unfiltered traversal graph
-> unique job URLs + discipline_map
-> per-job parsing
-> ranking
-> file writes
```

For Sioux specifically:

- `fetch_jobs.main()` resolves the source and drives the whole pipeline.
- `retrieve_sioux_job_links()` collects URLs through two parallel conceptual
  paths:
  - facet union
  - unfiltered pagination
- facet traversal builds `url -> disciplines`
- only after that does `fetch_source_jobs()` visit each detail page once
- `parser.fetch_job()` does:
  - deterministic extraction
  - LLM extraction
  - merge into one `SiouxJob`
- ranking and output writing happen after the full job list exists

## Why "Facet Thread Owns Job Immediately" Is Risky

Assume:

```text
Facet A -> URL X
Facet B -> URL X
```

If thread A sees `URL X` first and starts parsing immediately:

1. thread A records `URL X -> ["Facet A"]`
2. thread A parses the detail page
3. thread B later discovers `URL X -> ["Facet B"]`

Now `URL X` may already have been parsed with incomplete discipline data.

That race conflicts with the current contract that a parsed job receives the
full aggregated discipline list.

## Better Concurrency Shape

Use a two-stage pipeline.

### Stage 1: Concurrent URL Discovery Only

```text
entry page
-> extract facet list
-> facet worker pool
-> shared url_to_disciplines[url].add(facet)
-> barrier
-> sorted unique URL list
```

Each facet worker should do only:

- open its own Playwright context/page
- traverse the assigned facet pagination
- emit discovered job URLs
- update shared aggregation state

Shared state needed:

- `seen_urls` or simply `url_to_disciplines`
- a lock around updates
- deterministic final materialization after all workers finish

Important: parsing must not start until all facet workers complete.

### Stage 2: Concurrent Detail Parsing

```text
sorted unique URL list
-> detail worker pool
-> deterministic parse
-> LLM extraction
-> result slots
-> ordered jobs list
```

This is the safer place to parallelize aggressively because each unique URL is
already known and its full discipline list is already complete.

## Recommended Design

If we add concurrency, prefer this order:

1. Keep collection as a complete aggregation phase.
2. Optionally parallelize facet traversal for URL discovery only.
3. Parallelize detail-page parsing as a separate second phase.

This preserves correctness and still captures most of the speedup.

## Why Detail-Phase Parallelism Is the Best First Step

The detail phase is usually the dominant cost because each job requires:

- page navigation
- DOM extraction
- OpenAI LLM call

There are usually far more jobs than facets, so parallelizing detail parsing is
likely to reduce wall-clock time more than parallelizing only facets.

It also avoids the discipline aggregation race entirely.

## Constraints Before Any Implementation

### 1. Do Not Share Playwright Pages Across Threads

The current code uses one `detail_page` sequentially. In a threaded design,
each worker must own its own browser context and page.

### 2. Preserve Deterministic Output Order

Current outputs are effectively stable because URLs are sorted before detail
processing. A worker pool should either:

- store results by original index, or
- sort by URL before writing

### 3. Throttle LLM Concurrency

`parser.fetch_job()` includes one OpenAI call per job. Unbounded worker counts
will increase:

- rate-limit risk
- API error frequency
- spend per minute

A bounded pool is required.

### 4. Keep Validation Logic Intact

The facet-union vs unfiltered-paging comparison still requires a complete
collection phase before parsing begins.

## Practical Recommendation

Do not implement "facet thread discovers URL and immediately parses it."

Instead:

```text
Phase A: aggregate all URLs and disciplines
Phase B: parse each unique URL once with bounded worker concurrency
```

That design matches the current data dependencies and is much less likely to
introduce subtle correctness bugs.

## If We Decide To Implement

The safest rollout order would be:

1. Add concurrent detail parsing only.
2. Verify output equivalence and order stability.
3. Add bounded LLM concurrency.
4. Only then consider parallel facet traversal if collection time is still a
   bottleneck.
