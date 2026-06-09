# Adaptation Layer

Snapshot based on the current working tree on 2026-05-28.

## Scope

Reviewed files:

- `clients/base.py`
- `clients/registry.py`
- `clients/clients_cli.py`
- `clients/job_downloader.py`
- `clients/sources/browser_listing_adapter.py`
- `clients/sources/api_listing_adapter.py`
- `clients/sources/asml/adapter.py`
- `clients/sources/canon/adapter.py`
- `clients/sources/daf/adapter.py`
- `clients/sources/philips/adapter.py`
- `clients/sources/sioux/adapter.py`
- `clients/sources/vanderlande/adapter.py`

This document describes the current design. It does not propose or apply a refactor.

## Public Contract

`BaseClientAdapter` is the public adapter type used by the registry and callers.

Current API:

- `collect_job_links(*, job_limit: int) -> list[str]`
- `transform_downloaded_html(*, url: str, title: str | None, html_content: str) -> tuple[str | None, str]`

Current callers:

- `clients/registry.py` maps each `Client` enum value to a concrete adapter class and returns it as `BaseClientAdapter`.
- `clients/clients_cli.py` calls `adapter.collect_job_links(...)` in the collection path.
- `clients/job_downloader.py` calls `adapter.transform_downloaded_html(...)` after opening each job detail page and capturing browser HTML.

The public base therefore combines two responsibilities:

- Listing collection: finding job detail URLs.
- Downloaded-detail transformation: normalizing persisted job HTML after detail-page capture.

## Class Relationships

```text
BaseClientAdapter
├── BrowserListingAdapter
│   ├── AsmlClientAdapter
│   ├── DafClientAdapter
│   ├── SiouxBrowserListingAdapter
│   └── VanderlandeClientAdapter
└── APIListingAdapter
    ├── CanonAPIListingAdapter
    └── PhilipsAPIListingAdapter
```

Related DTOs:

- `PageAdvance`: browser pagination instruction.
- `AdvanceDecision`: browser pagination decision enum: `FOLLOW_URL`, `CLICK`, `STOP`.
- `APIPageResult`: API page parse result with `job_links`, `next_request_state`, `expected_total`, and `is_last_page`.

## Browser Adapter API

`BrowserListingAdapter` owns the Playwright browser lifecycle for link collection:

- `collect_job_links(...)` creates a browser.
- It opens a new browser context.
- It delegates source-specific behavior to `_collect_job_links_in_context(...)`.

Required subclass hooks:

- `_collect_job_links_in_context(context, *, job_limit) -> list[str]`
- `_get_job_links_from_page(page, log_context, *, job_limit) -> set[str]`
- `_get_page_advance(page) -> PageAdvance`
- `_get_next_page(page, page_advance) -> Any`

Shared helpers:

- `_open_page(...)`: opens a listing URL and applies common page preparation.
- `_collect_job_links_from_page_common(...)`: extracts and filters anchor URLs from a DOM page.
- `_get_page_advance_common(...)`: detects whether pagination should follow a URL, click, or stop.
- `_get_next_page_common(...)`: executes `FOLLOW_URL` or `CLICK`.
- `_collect_links_from_paginated_listing(...)`: loops through browser listing pages, deduplicates links, enforces `job_limit`, and applies pagination stop conditions.

Concrete browser behavior:

- `AsmlClientAdapter`, `DafClientAdapter`, and `VanderlandeClientAdapter` follow the simple pattern: open entry URL, collect paginated listing, return sorted URLs.
- `SiouxBrowserListingAdapter` first extracts discipline facets, then runs the common paginated-listing loop per facet with an expected sidebar count.
- `VanderlandeClientAdapter` also overrides `transform_downloaded_html(...)` to render Workday JSON-LD job detail HTML into a normalized HTML document.

## API Adapter API

`APIListingAdapter` owns API collection orchestration:

- `collect_job_links(...)` retries collection up to `_get_max_attempts()`.
- Each attempt calls `_collect_job_links_once(...)`.
- Links are deduplicated across attempts.
- The return value is sorted and truncated to `job_limit`.

Required subclass hooks:

- `_get_initial_request_state() -> Any`
- `_fetch_listing_response(request_state) -> Any`
- `_parse_listing_response(response, *, request_state, page_index, remaining_job_budget) -> APIPageResult`

Optional subclass hooks:

- `_get_max_attempts() -> int`
- `_get_jobs_count() -> int | None`
- `_get_request_state_key(request_state) -> str`

Concrete API behavior:

- `CanonAPIListingAdapter` uses `requests.Session`, page-number state, Canon filters, and parses `totalJobs`.
- `PhilipsAPIListingAdapter` uses `shared.api.ApiClient`, discovers the Netherlands facet ID first, then pages by Workday offset and parses `total`.

## Shared Runtime Shape

Both browser-based and API-based adapters implement the same public operation:

```text
collect_job_links(job_limit) -> sorted list of unique job detail URLs
```

They also share the same conceptual collection flow:

```text
initialize source state
loop pages/batches
  retrieve current listing data
  extract job links from current listing data
  deduplicate links
  enforce job_limit
  decide whether more listing data exists
  advance to next page/batch
return sorted links
```

The main difference is the retrieval mechanism:

- Browser adapters retrieve listing data through Playwright pages and DOM selectors.
- API adapters retrieve listing data through request state, HTTP responses, and response parsers.

## Sequence Flow

### Registry and CLI Collection

```text
clients_cli.main
  -> get_client_adapter(client)
       -> instantiate concrete adapter from clients/registry.py
  -> adapter.collect_job_links(job_limit=...)
  -> write collected links to disk
```

### Browser Collection

```text
BrowserListingAdapter.collect_job_links
  -> create_browser()
  -> browser.new_context()
  -> concrete_adapter._collect_job_links_in_context(context, job_limit)
       -> context.new_page()
       -> _open_page(page, entry_url or facet_url)
       -> _collect_links_from_paginated_listing(page, context, job_limit)
            -> _get_job_links_from_page(page, ...)
                 -> _collect_job_links_from_page_common(...)
            -> merge links into collected set
            -> _get_page_advance(page)
                 -> _get_page_advance_common(...)
            -> _get_next_page(page, page_advance)
                 -> _get_next_page_common(...)
       -> sorted(collected_links)
```

`SiouxBrowserListingAdapter` inserts a facet loop before the paginated listing loop:

```text
open entry page
extract discipline facets
for each facet
  open facet URL
  collect paginated listing for that facet
merge all facet links
return sorted links
```

### API Collection

```text
APIListingAdapter.collect_job_links
  -> max_attempts = _get_max_attempts()
  -> for each attempt
       -> _collect_job_links_once(job_limit)
            -> request_state = _get_initial_request_state()
            -> while request_state is not None
                 -> guard repeated request state
                 -> response = _fetch_listing_response(request_state)
                 -> page_result = _parse_listing_response(...)
                 -> merge page_result.job_links into collected set
                 -> stop on no new links, job limit, expected total, or last page
                 -> request_state = page_result.next_request_state
       -> merge attempt links into accumulated set
       -> stop on expected total or job limit
  -> sorted(accumulated_links)[:job_limit]
```

### Downloaded HTML Transformation

```text
clients_cli.main --download
  -> read saved job links
  -> create_browser(headless=True)
  -> download_job_html_pages(browser, links, adapter=adapter)
       -> open each job detail URL
       -> capture HTML and title
       -> adapter.transform_downloaded_html(...)
       -> persist returned HTML
```

Only `VanderlandeClientAdapter` currently has non-default transformation behavior. The base default returns the original title and HTML unchanged.

## Design Smells

### Base Interface Mixes Separate Responsibilities

`BaseClientAdapter` exposes both `collect_job_links(...)` and `transform_downloaded_html(...)`.

Those methods belong to different phases:

- `collect_job_links(...)` is a listing-source collection operation.
- `transform_downloaded_html(...)` is a job-detail post-processing operation used during download/persistence.

API listing adapters must inherit the HTML transformation method even though API collection does not need it. This is an Interface Segregation Principle smell and also weakens Single Responsibility at the public adapter boundary.

### Base Contract Is Not Enforced by ABC

`BaseClientAdapter` inherits from `ABC`, but `collect_job_links(...)` is not marked `@abstractmethod`. A subclass can be instantiated without implementing it and will fail only at runtime with `NotImplementedError`.

The current base acts more like a loose convention than a strictly enforced abstract interface.

### Shared Collection Flow Is Duplicated Across Browser and API Templates

Browser and API adapters have the same high-level collection lifecycle: initialize, retrieve page/batch, extract links, dedupe, enforce limit, decide next state, advance.

That lifecycle is implemented separately in:

- `BrowserListingAdapter._collect_links_from_paginated_listing(...)`
- `APIListingAdapter._collect_job_links_once(...)`
- `APIListingAdapter.collect_job_links(...)`

The mechanics differ, but the orchestration concerns are similar. This creates drift risk in stop conditions, logging, deduplication, retries, and completeness handling.

### Stop Conditions Are Inconsistent Between Browser and API Collection

API collection stops when a page yields no new links. Browser collection does not have the same no-new-links stop and instead continues to pagination detection.

This may be intentional for some browser sources, but it means the two adaptation families no longer share the same completeness semantics even though they expose the same public operation.

### API Collection Has Dead or Incomplete Hook Surface

`APIListingAdapter.collect_job_links(...)` assigns `jobs_count = self._get_jobs_count()`, but the value is not used.

This makes `_get_jobs_count()` look like part of the extension contract even though it has no effect. It is either dead code or an unfinished completeness feature.

### API Initial State Type Is Inaccurate

`APIListingAdapter._get_initial_request_state()` is typed as returning `Any`, but `_collect_job_links_once(...)` supports `None` as the no-work/no-state outcome.

`PhilipsAPIListingAdapter._get_initial_request_state()` already returns `PhilipsPageState | None` when the required country facet cannot be discovered. The abstract hook type does not communicate that valid behavior.

### APIPageResult Invariants Are Implicit

`APIPageResult` can represent conflicting states, for example `is_last_page=False` with `next_request_state=None`.

The loop will still stop because `request_state` becomes `None`, but the reason is implicit. The DTO does not enforce or document invariants between `next_request_state` and `is_last_page`.

### Browser Subclasses Contain Boilerplate Forwarding Methods

Most browser subclasses implement `_get_next_page(...)` only to call `_get_next_page_common(...)` with a click helper or no helper.

Several subclasses also implement `_collect_job_links_in_context(...)` with the same sequence: create page, open entry URL, collect paginated listing, log count, return sorted links.

This is a sign that the browser base class is asking subclasses to repeat orchestration code instead of only supplying source-specific mechanics.

### Browser Pagination State Is URL-Centric

`BrowserListingAdapter._collect_links_from_paginated_listing(...)` tracks visited pages by `page.url`.

That works for URL-follow pagination. It is weaker for click-based pagination where the visible listing state may change without the URL changing. In that case, repeated URL detection can skip collection for later pages even though the DOM changed.

### Browser Next-Page Detection Prefers Href Before Disabled/Click Semantics

`_get_page_advance_common(...)` follows a normalized `href` before checking whether the element is a usable click-next control.

For next controls that are anchors with disabled state, this can make disabled/link-validity semantics source-dependent and easy to get wrong.

### Vanderlande Adapter Has Duplicate Method Definitions

`VanderlandeClientAdapter` defines `_collect_links_from_paginated_listing(...)` twice.

The later definition overrides the earlier one and drops the `expected_count` parameter. That is likely accidental shadowing and makes the class harder to reason about.

### Public Adapter Type Couples Listing and Detail Download Workflows

The registry returns every concrete adapter as `BaseClientAdapter`. The CLI then passes that same adapter into both collection and download code.

This creates a single object role for:

- Listing retrieval.
- Browser detail-page post-processing.

The design works because `transform_downloaded_html(...)` has a no-op default, but the dependency direction is broad: download code depends on the full listing adapter type when it only needs an optional HTML transformer.

### Heavy Use of Any Weakens Adapter Boundaries

The adaptation layer uses `Any` for browser contexts/pages, request states, API responses, and returned page objects.

Some of this is pragmatic for Playwright and heterogeneous APIs, but it means source-specific contracts are not checked by type hints. Mistakes in hook compatibility are mostly caught by tests or runtime behavior.
