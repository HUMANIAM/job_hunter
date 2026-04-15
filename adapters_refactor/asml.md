Refactor `clients/sources/asml/adapter.py` to use `clients/sources/browser_listing_adapter.py`, using `clients/sources/sioux/adapter.py` as the reference shape.

Scope:
- Keep the public adapter class name as `AsmlClientAdapter`.
- Keep the package exports in `clients/sources/asml/__init__.py` working as they do now.
- Do not change collection behavior beyond moving the shared browser-listing logic into `BrowserListingAdapter`.

What to preserve from the current ASML adapter:
- Entry URL: `ASML_ENTRY_URL`
- Results-ready selectors: `ASML_RESULTS_READY_SELECTORS`
- Cookie accept selectors: `ASML_COOKIE_ACCEPT_SELECTORS`
- Job URL filtering:
  - `ASML_JOB_URL_RE`
  - `ASML_WORKDAY_JOB_URL_RE`
- Listing anchor selector: `a[href]`
- Pagination selectors, in the same order:
  - `button[aria-label='next']`
  - `a[aria-label='Next']`
  - `a[rel='next']`
  - `a.pagination__next`
  - `button[aria-label='Next']`
- Pagination behavior:
  - If the next control has an `href`, follow it.
  - If the control is a `button`, treat it as click-based pagination.
  - Keep the tag-name check based on `element.evaluate("(el) => el.tagName.toLowerCase()")`.
  - Disabled detection for click pagination must stay the same: check `disabled`, `aria-disabled == "true"`, and `"disabled"` in the class name.
  - After clicking next, keep the existing `page.wait_for_timeout(1500)`.

Implementation expectations:
- Change the adapter to subclass `BrowserListingAdapter`, not `BaseClientAdapter`.
- Align `_collect_job_links_in_context` with the Sioux/browser-listing pattern: create the page from `context.new_page()` inside the method. Do not keep the outdated `page` parameter.
- Move shared page opening to the base helper by setting:
  - `entry_url`
  - `listing_label`
  - `results_ready_selectors`
  - `cookie_accept_selectors`
- Replace the old `__CLICK_NEXT__` sentinel flow with `PageAdvance` / `AdvanceDecision`.
- Implement client-specific methods in the same style as Sioux:
  - `_get_job_links_from_page(...)`
  - `_get_page_advance(...)`
  - `_get_next_page(...)`
- Reuse the common helpers from `BrowserListingAdapter` where they fit:
  - `_collect_job_links_from_page_common(...)`
  - `_get_page_advance_common(...)`
  - `_get_next_page_common(...)`
  - `super()._collect_links_from_paginated_listing(...)`
- Keep the existing URL normalization and job filtering behavior exactly as-is. This is a structural refactor, not a scraping logic change.

Tests to update:
- Update `tests/unit/clients/test_asml_adapter.py` to match the new abstraction.
- Replace expectations around `_get_next_page_url()` / `__CLICK_NEXT__` with assertions on `PageAdvance`.
- Add coverage that `_get_next_page(...)` executes click-based pagination and preserves the `1500` ms wait.
- Keep the existing job-link filtering coverage, including the accepted ASML and Workday job URLs.
- Follow `tests/unit/clients/test_sioux_adapter.py` for the `PageAdvance`-style tests and fake objects.

Verification:
- Run `pytest tests/unit/clients/test_asml_adapter.py tests/unit/clients/test_registry.py`
- If registry imports or class references need adjustment, keep them minimal and verify them in the same run.
