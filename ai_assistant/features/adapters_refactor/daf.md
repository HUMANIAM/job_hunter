Refactor `clients/sources/daf/adapter.py` to use `clients/sources/browser_listing_adapter.py`, using `clients/sources/sioux/adapter.py` as the reference shape.

Scope:
- Keep the public adapter class name as `DafClientAdapter`.
- Keep the package exports in `clients/sources/daf/__init__.py` working as they do now.
- Do not change behavior beyond moving the shared browser-listing flow into `BrowserListingAdapter`.

What to preserve from the current DAF adapter:
- Entry URL: `DAF_ENTRY_URL`
- Results-ready selectors: `DAF_RESULTS_READY_SELECTORS`
- Cookie accept selectors: `DAF_COOKIE_ACCEPT_SELECTORS`
- Job URL filtering: `DAF_JOB_URL_RE`
- Listing anchor selector: `a.vacancy-item__link[href]`
- Pagination selector: `a.page-link.page-link--next`
- Pagination behavior:
  - If the next control has an `href`, follow that URL.
  - If there is no `href` and `data-page == "next"`, treat it as click-based pagination.
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
- Keep the existing logging intent and stop conditions. This refactor should remove duplicated pagination code, not alter collection semantics.

Tests to update:
- Update `tests/unit/clients/test_daf_adapter.py` to match the new abstraction.
- Replace expectations around `_get_next_page_url()` / `__CLICK_NEXT__` with assertions on `PageAdvance`.
- Add coverage that `_get_next_page(...)` executes click-based pagination and preserves the `1500` ms wait.
- Keep the existing job-link filtering coverage.
- Update/add any small fake test helpers needed for `PageAdvance`-based assertions, following `tests/unit/clients/test_sioux_adapter.py` as the pattern.

Verification:
- Run `pytest tests/unit/clients/test_daf_adapter.py tests/unit/clients/test_registry.py`
- If registry imports or class references need adjustment, keep them minimal and verify them in the same run.
