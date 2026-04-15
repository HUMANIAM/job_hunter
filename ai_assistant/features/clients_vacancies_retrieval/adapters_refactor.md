# Adapters Refactor Assessment

## Executive Summary

Your mental model is close, but the stable retrieval model is slightly broader:

`entry point -> optional seed discovery -> load current result page -> extract candidate job links -> filter/normalize -> advance pagination cursor -> repeat -> optional HTML post-processing`

The current adapters mix all of those concerns inside each client class. The main refactor opportunity is not "make one universal adapter", but "extract one reusable collection pipeline with small, explicit strategies for seeds, page/result loading, extraction, and pagination".

The low-risk path is:

1. Extract a shared browser-listing base for the dominant pattern.
2. Add reusable pagination strategies.
3. Add a seed/facet traversal helper for `Sioux`.
4. Add a separate API-listing base for `Philips`.
5. Keep site-specific extraction and filtering logic local to each adapter.

## What The Code Actually Does Today

| Adapter | Seed model | Result source | Pagination model | Site-specific filtering |
| --- | --- | --- | --- | --- |
| `ASML` | Single entry URL | Browser DOM | Next control, sometimes click-based | Regex match for ASML and Workday URLs |
| `DAF` | Single entry URL | Browser DOM | Next control, sometimes click-based | Regex match, excludes non-job vacancy pages |
| `Vanderlande` | Single entry URL | Browser DOM | Next control, sometimes click-based | Regex match, strips query params, HTML post-transform |
| `Canon` | Single entry URL | Browser DOM | Query param page number | Card location must contain `Netherlands` |
| `Sioux` | Entry page fan-out into discipline facets | Browser DOM | Next href inside each facet | Regex match plus per-facet expected-count stop |
| `Philips` | Single entry URL plus discovered Netherlands facet id | Workday JSON API | Offset-based API pagination | Detail page fetch validates Netherlands country |

That means the true common model is not only "open page, grab links, click next". There are four separable axes:

1. How seeds are discovered.
2. How one result page is loaded.
3. How job links are extracted and filtered.
4. How the next page/cursor is computed.

## Where The Duplication Is

### 1. Adapter lifecycle and collection entrypoint

All six adapters repeat the same entrypoint pattern: the public `collect_job_links(...)`
method delegates immediately to a private collection helper:

- `clients/sources/asml/adapter.py:39`
- `clients/sources/canon/adapter.py:33`
- `clients/sources/daf/adapter.py:36`
- `clients/sources/philips/adapter.py:35`
- `clients/sources/sioux/adapter.py:22`
- `clients/sources/vanderlande/adapter.py:33`

`BaseClientAdapter` in `clients/base.py:6` captures the public method shape, but it
still does not describe the retrieval protocol that all concrete adapters are
following.

### 2. Page opening and preparation

Every browser-driven adapter wraps `open_and_prepare_page(...)` with the same structure:

- open URL
- wait for result selectors
- optionally dismiss cookies
- log current URL

This repeats in:

- `ASML` at `clients/sources/asml/adapter.py:49`
- `Canon` at `clients/sources/canon/adapter.py:43`
- `DAF` at `clients/sources/daf/adapter.py:46`
- `Sioux` at `clients/sources/sioux/adapter.py:33`
- `Vanderlande` at `clients/sources/vanderlande/adapter.py:57`

### 3. Browser pagination loop

`ASML`, `DAF`, and `Vanderlande` all contain nearly the same browser listing loop:

- collect links from current page
- build a repeat-detection key
- merge unique links
- stop on job limit
- discover next page
- follow href or click next

The duplicated blocks are:

- `ASML` `clients/sources/asml/adapter.py:97-213`
- `DAF` `clients/sources/daf/adapter.py:91-200`
- `Vanderlande` `clients/sources/vanderlande/adapter.py:97-212`

This is the strongest refactor seam in the whole adapter layer.

### 4. Browser context/page lifecycle

Opening a browser context, creating a page, invoking collection, and returning `sorted(...)` is repeated in every adapter, even when the only difference is which private helper runs.

### 5. Merge/log/stop logic across non-browser flows

Even when the pagination mechanism changes, the same orchestration keeps reappearing:

- `Canon` `clients/sources/canon/adapter.py:122-163`
- `Philips` `clients/sources/philips/adapter.py:150-212`
- `Sioux` `clients/sources/sioux/adapter.py:111-169`

The data source changes, but the loop shape is still "load page -> extract -> merge -> stop -> advance".

## Recommended Target Design

### 1. Define the adapter protocol explicitly

The first step should be to document the retrieval protocol on `BaseClientAdapter`
level, instead of describing that contract indirectly inside one concrete
realization.

The public protocol should stay small:

```python
class BaseClientAdapter(ABC):
    def collect_job_links(
        self,
        browser: Any,
        *,
        job_limit: int,
    ) -> list[str]:
        raise NotImplementedError

    def transform_downloaded_html(...) -> tuple[str | None, str]:
        ...
```

Recommended contract for `collect_job_links(...)`:

- `job_limit` is already normalized before the adapter is called.
- The adapter owns one collection run end-to-end.
- Browser-driven realizations may open one Playwright browser context for that run.
- The returned URLs are job-detail URLs, deduplicated, deterministic, and sorted.
- The adapter realization is responsible for source-specific traversal, filtering,
  and pagination.
- The adapter instance itself should stay stateless across runs.

Recommended contract for `transform_downloaded_html(...)`:

- It is optional and independent from link collection.
- It may normalize downloaded job HTML, but it does not participate in pagination
  or link discovery.

Different realizations can satisfy the same protocol with different result sources:

- `BrowserListingAdapter` for DOM-driven listing pages
- `SeededBrowserListingAdapter` for DOM-driven listings that first fan out into
  multiple seeds or facets
- `ApiListingAdapter` for API-driven result streams

That gives reuse without forcing `Philips` into a Playwright-shaped abstraction.

### 2. `BrowserListingAdapter` as one protocol realization

`BrowserListingAdapter` should document what is specific about browser listing
pages and how that realization fulfills the shared adapter protocol.

Suggested shape:

```python
class BrowserListingAdapter(BaseClientAdapter):
    entry_url: str
    ready_selectors: Sequence[str]
    cookie_selectors: Sequence[str] = ()
    listing_label: str
    pagination: BrowserPaginationStrategy

    def _extract_links_from_page(
        self,
        page: Page,
        *,
        remaining: int,
        log_context: str,
    ) -> set[str]:
        raise NotImplementedError
```

`BrowserListingAdapter` is specific to clients where:

- the result source is the current page DOM
- the collection run starts from one browser entry URL
- pagination stays inside the listing surface

How `BrowserListingAdapter` implements the shared adapter contract:

- open one Playwright browser context and initial page for the run
- open `entry_url`
- apply shared page preparation using `ready_selectors` and `cookie_selectors`
- iterate listing pages using the configured pagination strategy
- call `_extract_links_from_page(...)` on each page
- enforce `job_limit`
- detect repeated page state
- merge unique links and return them in sorted order
- emit generic progress logs using `listing_label`

What the subclass contract should be:

- provide `entry_url`
- provide readiness and cookie selectors
- provide a `listing_label`
- provide a pagination strategy
- implement `extract_links_from_page(...)`

What `_extract_links_from_page(...)` should own:

- find candidate elements on the current page
- turn them into absolute job URLs
- normalize and filter those URLs
- return only the links visible on the current page

What it should not own:

- creating or closing the browser context
- page-to-page iteration
- deduplication across pages
- final sorting
- generic stop logic

`ASML`, `DAF`, and `Vanderlande` should become mostly configuration plus
`extract_links_from_page(...)`. `Canon` should also fit this realization, but with
`QueryParamPagination` instead of a next-control strategy.

### 3. Introduce pagination strategies instead of hardcoding next-page logic in adapters

Add small strategy objects or helper classes for page progression:

- `NextControlPagination`
- `QueryParamPagination`
- `OffsetPagination`

Suggested mapping:

- `ASML`, `DAF`, `Vanderlande` -> `NextControlPagination`
- `Canon` -> `QueryParamPagination`
- `Philips` -> `OffsetPagination`

Important detail: `NextControlPagination` needs explicit modes instead of a loose sentinel string like `__CLICK_NEXT__`.

For example:

```python
@dataclass(frozen=True)
class PaginationAction:
    kind: Literal["follow_url", "click", "stop"]
    url: str | None = None
```

That removes the current string sentinel coupling used in:

- `ASML` `clients/sources/asml/adapter.py:120`
- `DAF` `clients/sources/daf/adapter.py:108`
- `Vanderlande` `clients/sources/vanderlande/adapter.py:117`

### 4. Extract seed discovery as a first-class concept

`Sioux` proves that "one entry URL" is not the whole model. The entry page sometimes produces a set of listing seeds.

Introduce a seed abstraction:

- `SingleEntrySeed(entry_url)`
- `FacetSeedDiscovery(discover(page) -> list[Seed])`

Where a `Seed` can hold:

- name
- url
- optional expected count

Then `Sioux` becomes a standard seeded browser listing instead of a custom control flow living entirely inside the adapter.

### 5. Keep API-backed collection separate from browser collection

`Philips` should not be bent into the same base as Playwright DOM collectors. It has a distinct shape:

- discover Netherlands facet id
- fetch paginated JSON payloads
- derive job URLs from `externalPath`
- validate location through detail page content

That deserves its own base:

```python
class ApiListingAdapter(BaseClientAdapter):
    def fetch_page(self, cursor: Any, *, remaining: int) -> ApiPage:
        raise NotImplementedError

    def extract_links_from_payload(...) -> set[str]:
        raise NotImplementedError

    def next_cursor(...) -> Any | None:
        raise NotImplementedError
```

This keeps the shared merge/stop loop reusable without pretending the source is a browser page.

### 6. Standardize small site hooks, not giant inheritance trees

For 200+ clients, the winning shape is "config first, hook second". A new simple client should mostly declare:

- entry URL
- ready selectors
- cookie selectors
- card selector
- URL matcher or normalizer
- pagination strategy

Only clients with real complexity should override hooks.

If a new adapter needs more than one page of custom control flow, that is a signal it should use a specialized base or stay custom.

## What Should Stay Site-Specific

Do not abstract these away too early:

- Regexes or URL normalizers for valid job detail pages.
- Card-level filters like Canon's `Netherlands` location check.
- Detail-page validation like Philips' `addressCountry` check.
- Seed extraction DOM for Sioux facets.
- HTML post-processing like Vanderlande's `transform_downloaded_html(...)`.

Those are the pieces most likely to break per site and should stay close to the adapter definition.

## Suggested Migration Order

1. Extract shared page-open preparation helper into a browser-listing base.
2. Migrate `ASML`, `DAF`, and `Vanderlande` onto one shared `BrowserListingAdapter` plus `NextControlPagination`.
3. Migrate `Canon` onto the same browser base with `QueryParamPagination`.
4. Extract `Seed` discovery and migrate `Sioux` onto `SeededBrowserListingAdapter`.
5. Extract `ApiListingAdapter` and migrate `Philips`.
6. Only after those moves, consider moving simple adapters from future clients to config-only definitions.

This order matters because it starts with the cleanest duplication and avoids designing the whole framework around outliers.

## Testing Strategy For The Refactor

Before migrating many clients, add shared strategy tests around the new collector layer:

- next-control pagination follows hrefs correctly
- next-control pagination clicks when configured
- repeated page state stops the loop
- query-param pagination increments correctly
- seed traversal deduplicates across facets
- offset pagination stops on empty or partial result pages

Keep thin adapter-specific tests for site behavior that should remain local:

- `ASML` URL filtering
- `DAF` exclusion of non-job vacancy pages
- `Canon` Netherlands location filter
- `Sioux` facet parsing
- `Philips` Netherlands detail-page validation
- `Vanderlande` query stripping and HTML transform

## Bottom Line

The right refactor is:

- one reusable collection pipeline
- two concrete collector families (`browser` and `api`)
- one optional seed-discovery layer
- small pagination strategies
- small site-specific extraction hooks

That should make the common case for a new client "declare config and one extractor", while still leaving room for custom flows like `Sioux` and `Philips` without distorting the shared design.
