Refactor `clients/sources/vanderlande/adapter.py` to use `clients/sources/browser_listing_adapter.py`, using `clients/sources/sioux/adapter.py` as the reference shape.

Scope:
- Keep the public adapter class name as `VanderlandeClientAdapter`.
- Keep `transform_downloaded_html(...)` and its current behavior intact.
- Do not change scraping behavior beyond moving the shared browser-listing flow into `BrowserListingAdapter`.

What to preserve from the current Vanderlande adapter:
- Entry URL: `VANDERLANDE_ENTRY_URL`
- Results-ready selectors: `VANDERLANDE_RESULTS_READY_SELECTORS`
- Job URL filtering: `VANDERLANDE_JOB_URL_RE`
- Listing anchor selector: `a[data-automation-id='jobTitle'][href]`
- Link normalization: resolve relative URLs against `page.url` and strip the query string with `.split("?", 1)[0]`
- Pagination selectors, in the same order:
  - `button[aria-label='next']`
  - `button[data-uxi-element-id='next']`
  - `button[aria-label='Next']`
  - `a[aria-label='Next']`
- Pagination behavior:
  - If the next control has an `href`, follow it.
  - If the control is a `button`, treat it as click-based pagination.
  - Keep the tag-name check based on `element.evaluate("(el) => el.tagName.toLowerCase()")`.
  - Disabled detection for click pagination must stay the same: check `disabled`, `aria-disabled == "true"`, and `"disabled"` in the class name.
  - After clicking next, keep the existing `page.wait_for_timeout(1500)`.
- `transform_downloaded_html(...)` must continue delegating to `render_vanderlande_job_html(...)` exactly as it does now.

Implementation expectations:
- Change the adapter to subclass `BrowserListingAdapter`, not `BaseClientAdapter`.
- Align `_collect_job_links_in_context` with the Sioux/browser-listing pattern: create the page from `context.new_page()` inside the method. Do not keep the outdated `page` parameter.
- Move shared page opening to the base helper by setting:
  - `entry_url`
  - `listing_label`
  - `results_ready_selectors`
- There are no cookie selectors today; keep that behavior unchanged.
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
- Keep the existing HTML transformation method and any imports it relies on.

Tests to update:
- Add `tests/unit/clients/test_vanderlande_adapter.py`; there is no current unit file for this adapter.
- Cover:
  - job-link filtering and query-string stripping
  - click-based pagination detection via `PageAdvance`
  - `_get_next_page(...)` click execution and the `1500` ms wait
  - `transform_downloaded_html(...)` preserving the current delegation behavior
- Follow `tests/unit/clients/test_sioux_adapter.py` for `PageAdvance`-style assertions and fake page helpers.

Verification:
- Run `pytest tests/unit/clients/test_vanderlande_adapter.py`
- If registry imports or package exports need adjustment, keep them minimal and run the relevant registry test coverage too.
