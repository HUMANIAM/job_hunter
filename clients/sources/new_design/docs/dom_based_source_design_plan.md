# DOM-Based Vacancy Source Plan

## Goal

Migrate DOM-based vacancy link retrieval to the new abstraction layer without
rewriting the working Sioux behavior from scratch.

The DOM path must expose the same client-facing contract as the API path:

```text
VacancySource.get_vacancy_links(criteria) -> VacancyLinks
```

The caller must not know whether links came from HTTP API calls or rendered DOM
pages.

## Current Reference Behavior

The existing Sioux implementation is the reference behavior.

It currently does this:

- Opens the Sioux entry URL.
- Accepts the cookie banner when present.
- Waits until vacancy cards are available.
- Extracts discipline facets from the sidebar.
- For each discipline facet:
  - opens the facet URL
  - extracts visible vacancy links from the current listing page
  - follows the next page URL when available
  - stops when the facet expected count is reached, the job limit is reached,
    the next page repeats, or no next page exists
- Deduplicates links across facets.
- Returns vacancy detail URLs.

Important existing Sioux data:

- entry URL: `https://vacancy.sioux.eu/`
- vacancy card selector: `a.act-item-job-overview`
- cookie accept selector: `input.cookieClose.cookieAccept`
- discipline facet selector:
  `div.facets_item[data-type='functiegr'] a.filter-item-link`
- next page selector:
  `div.overview-paging-controls a.paging-item-next`
- valid vacancy URL pattern:
  `https://vacancy.sioux.eu/vacancies/*.html`

## Target New Design

Required new classes and modules:

- `BrowserAccess` IF
- `PlaywrightBrowserAccess` realization
- `SiouxVacancyLinkRetriever`
- `SiouxVacancySource`
- `sioux_vacancy_source_provider`
- registry wiring in `create_vacancy_source_registry`
- focused tests for Sioux retriever behavior

Use `SiouxVacancySource`, not `SiouxSourceVacancy`.

## Responsibilities

### BrowserAccess IF

Mechanism IF for rendered DOM access.

Responsibility:

- Hide Playwright from retrievers.
- Own browser/context/page lifecycle details.
- Open listing URLs and prepare the page.
- Provide only the DOM operations needed by vacancy link retrieval.

Minimum capabilities needed by Sioux:

- open a URL and wait for configured selectors
- click configured selectors if visible, for cookie banners
- return the current page URL
- read repeated elements by selector
- read element text and attributes

Do not expose Playwright page, locator, browser, or context objects through the
domain layer.

### PlaywrightBrowserAccess

Realization of `BrowserAccess`.

Responsibility:

- Use the existing `infra.browser.create_browser` and
  `infra.browser.open_and_prepare_page` behavior.
- Manage browser/context/page lifetime.
- Translate Playwright-specific failures into BrowserAccess-level failures when
  that error contract is introduced.

### SiouxVacancyLinkRetriever

Realization of `VacancyLinkRetriever`.

Responsibility:

- Express the existing Sioux facet traversal as cursor-based retrieval batches.
- Depend on `BrowserAccess`, not Playwright.
- Keep Sioux selectors, URL normalization, and URL validation in Sioux-specific
  modules.
- Return `VacancyLinkBatch` values to the shared workflow.

The retriever should keep Sioux-specific cursor state private. The base
`VacancyLinkRetriever` should not know about facets, selectors, pages, or next
page URLs.

### SiouxVacancySource

Realization of `VacancySource`.

Responsibility:

- Be the client-facing source object for Sioux vacancy links.
- Delegate to `VacancyLinkRetriever`.
- Contain no Playwright, selector, pagination, or facet logic.

### Provider And Registry Wiring

`sioux_vacancy_source_provider` should create:

```text
BrowserAccess -> SiouxVacancyLinkRetriever -> SiouxVacancySource
```

`create_vacancy_source_registry` should own the mechanism lifetime:

```text
PlaywrightBrowserAccess
RequestsHttpAccess
VacancySourceRegistry
```

Each source should receive its own mechanism instance unless there is a clear
reason to share one.

## Cursor Model

Sioux retrieval is not a simple numbered pagination flow. It is a nested flow:

```text
facets -> pages inside each facet
```

The cursor should model the minimum private state needed to continue retrieval.

Suggested private cursor fields:

- `facets`: discovered Sioux facet list
- `facet_index`: current facet position
- `facet_page_url`: current page URL inside the active facet
- `expected_count`: expected link count for the active facet, when available
- `visited_page_urls`: page URLs already visited inside the active facet

This cursor belongs to `SiouxVacancyLinkRetriever`, not the shared base class.

## Retrieval Flow

### Initial Cursor

`SiouxVacancyLinkRetriever._get_initial_cursor(criteria)` should:

- open the Sioux entry URL through `BrowserAccess`
- discover discipline facets
- return `None` when no facets are available
- otherwise return a cursor pointing to the first facet URL

### Listing Batch

`SiouxVacancyLinkRetriever._retrieve_listing_batch(cursor, progress)` should:

- open the cursor's current facet page URL
- extract vacancy links from the current page
- compute the next cursor:
  - next page in same facet when next page URL exists and was not visited
  - first page of next facet when the current facet is complete
  - `None` when all facets are complete
- return `VacancyLinkBatch(retrieved_links, next_cursor)`

Completion is still represented by `next_cursor is None`.

## Stop Conditions

Shared base stop conditions already cover:

- `next_cursor is None`
- `criteria.links_limit` reached

Sioux-specific stop conditions belong in `SiouxVacancyLinkRetriever`:

- current facet expected count reached
- next page URL is missing
- next page URL already visited
- current page has no valid vacancy links and no next page

## Data Modules

Keep Sioux-specific constants outside the generic classes.

Suggested files:

- `sioux_config.py`
- `sioux_response_parser.py` is not needed; this is DOM-based
- `sioux_dom_parser.py` or `sioux_listing_parser.py` for DOM extraction helpers
- `sioux_vacancy_link_retriever.py`
- `sioux_vacancy_source.py`
- `sioux_vacancy_source_provider.py`

Do not introduce parser modules until there is real extraction logic to isolate.

## Migration Steps

1. Expand `BrowserAccess` to the minimum operations needed by Sioux.
2. Add `PlaywrightBrowserAccess` using existing browser infrastructure.
3. Add Sioux config constants copied from the current adapter.
4. Add `SiouxVacancySource`.
5. Add `SiouxVacancyLinkRetriever` with private cursor state.
6. Add `sioux_vacancy_source_provider`.
7. Register Sioux in `create_vacancy_source_registry`.
8. Add focused tests for:
   - registry returns Sioux source
   - Sioux retriever extracts links from one page
   - Sioux retriever advances to next page
   - Sioux retriever advances to next facet
   - repeated page URL stops retrieval
   - link limit is respected
9. Run old and new Sioux collection and compare link sets.
10. Keep the old adapter until the new path is verified against live Sioux.

## Non-Goals

- Do not redesign vacancy page HTML downloading.
- Do not expose Playwright objects through `VacancySource` or
  `VacancyLinkRetriever`.
- Do not generalize for all DOM sources before Sioux is migrated.
- Do not add source-specific fields to `VacancyLinkRetrievalCriteria` unless a
  real caller needs them.

## Acceptance Criteria

- Running the new Sioux path returns the same vacancy link set as the old Sioux
  adapter for an unrestricted collection.
- `VacancySourceRegistry` can provide both Philips and Sioux sources.
- API-based and DOM-based sources both use:
  `VacancySource.get_vacancy_links(criteria)`.
- No Playwright object crosses the `BrowserAccess` boundary.
- Tests cover the Sioux cursor transitions and limit handling.
