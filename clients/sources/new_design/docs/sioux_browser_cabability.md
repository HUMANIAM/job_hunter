# Sioux Browser Capability Investigation

## Purpose

This note explains the browser capabilities needed by the new Sioux vacancy
link retriever.

The reference behavior is the old `SiouxBrowserListingAdapter`. The goal is not
to redesign the Sioux scraper. The goal is to express the same flow through a
small `BrowserAccess` interface so the Sioux retriever does not know about
Playwright pages, locators, contexts, or browsers.

## Mental Model

There are three separate responsibilities:

- `BrowserAccess`: opens pages and returns DOM elements from the current page.
- `SiouxVacancyLinkRetriever`: owns the traversal flow and cursor state.
- `sioux_dom_parser`: turns `DOMElement` values into Sioux-specific data.

The browser access object has one active page. Calling `open_url(url)` changes
that active page to the requested URL. Calling `find_elements(selector)` reads
from whichever page is currently active.

That means there is no special "facet page object" capability. A facet page is
just the current active page after the retriever opens a facet URL.

## Sioux Flow

### 1. Open The Entry Page

The retriever starts by opening the Sioux entry page:

```text
https://vacancy.sioux.eu/
```

The browser must wait until vacancy cards are present and click the cookie
accept control when it is visible.

This matches the old adapter:

```python
self._open_page(page, self.entry_url)
```

where `_open_page` calls:

```python
open_and_prepare_page(
    page,
    url,
    wait_for=self.results_ready_selectors,
    click_if_visible_selectors=self.cookie_accept_selectors,
)
```

### 2. Read Discipline Facet Elements

After the entry page is open, the retriever needs the sidebar facet elements:

```text
div.facets_item[data-type='functiegr'] a.filter-item-link
```

The old adapter did this directly with Playwright:

```python
links = page.locator(SIOUX_DISCIPLINE_FACET_SELECTOR)
```

The new retriever should do the same operation through `BrowserAccess`:

```python
facet_elements = browser_access.find_elements(
    config.SIOUX_DISCIPLINE_FACET_SELECTOR
)
```

### 3. Parse Facet Metadata

Each facet element contains:

- the facet name, from `.filter-item-link-name`
- the facet expected count, from `.filter-item-link-count`
- the facet URL, from the element `href`

This step is not a browser traversal concern. It belongs in
`sioux_dom_parser.extract_discipline_facets(...)`.

The result is:

```text
[(facet_name, facet_url, expected_count), ...]
```

Example shape:

```text
("Software", "https://vacancy.sioux.eu/...", 12)
```

### 4. Traverse Facets One By One

The retriever then loops over the facet metadata.

For each facet:

1. Open the facet URL.
2. Extract vacancy card links from the current facet page.
3. Look for a next-page link.
4. If a next-page URL exists and has not already been visited, open it.
5. Repeat until the facet is complete.
6. Move to the next facet.

Conceptually:

```text
entry page
  -> discover facets
  -> facet 1 page 1
  -> facet 1 page 2
  -> facet 1 complete
  -> facet 2 page 1
  -> facet 2 page 2
  -> facet 2 complete
  -> all facets complete
```

The retriever should deduplicate links across all facets.

### 5. Extract Vacancy Links From Current Facet Page

After opening a facet URL, the active browser page is now that facet page.

The retriever needs the vacancy card elements:

```text
a.act-item-job-overview
```

The old adapter did:

```python
links = page.locator(candidates_selector)
href = links.nth(index).get_attribute("href")
```

The new flow should be:

```python
job_elements = browser_access.find_elements(config.SIOUX_RESULTS_READY_SELECTOR)
```

Then the Sioux parser or retriever reads `href` from each `DOMElement`, joins it
against the entry URL, validates it against the Sioux vacancy URL pattern, and
adds it to the collected link set.

### 6. Find The Next Page URL

After reading job cards from the current facet page, the retriever checks for
the next page control:

```text
div.overview-paging-controls a.paging-item-next
```

The old adapter did:

```python
element = page.locator(selector).first
href = element.get_attribute("href")
```

The new flow can use the same `find_elements(...)` capability:

```python
next_elements = browser_access.find_elements(config.SIOUX_NEXT_PAGE_SELECTOR)
```

If the first returned element has an `href`, the retriever normalizes that URL
and uses it as the next page URL. Sioux does not currently need click-based
pagination because the old Sioux adapter always follows the next-page `href`.

### 7. Stop The Current Facet

The retriever stops traversing the active facet when any of these are true:

- the global link limit has been reached
- there is no next-page URL
- the next-page URL was already visited
- the current page URL repeats

The expected count comes from facet metadata and is useful for logging and for
skipping facets with non-positive counts. It should not be used as a hard
extraction cap because Sioux can expose more valid cards on a facet page than
the sidebar count suggests. The visited-page checks need the browser's current
URL.

### 8. Move To The Next Facet

When a facet is complete, the retriever does not need a new browser page or a
new browser context. It opens the next facet URL on the same active page:

```python
browser_access.open_url(next_facet_url, ...)
```

The old adapter also reused the same Playwright page for all facets and pages.

## Required Browser Capabilities

### `open_url(url, wait_for_selectors, click_if_visible_selectors)`

Needed for:

- opening the entry page
- opening each facet URL
- opening each next-page URL
- waiting until Sioux vacancy cards are present
- accepting the cookie banner when visible

Why Sioux needs it:

The old adapter always opened listing pages through `_open_page(...)`, which
called `open_and_prepare_page(...)` with wait selectors and cookie selectors.
The new browser access must preserve that behavior.

### `find_elements(selector) -> list[DOMElement]`

Needed for:

- finding discipline facet elements on the entry page
- finding vacancy card elements on each facet page
- finding next-page anchor elements on each facet page

Why Sioux needs it:

The old adapter repeatedly used `page.locator(selector)`, `count()`, and
`nth(index)` to inspect DOM collections. The new retriever needs the same DOM
selection ability, but it must receive `DOMElement` wrappers instead of
Playwright locators.

This is the main bridge between the active browser page and the Sioux parser.

### `current_url() -> str`

Needed for:

- recording visited pages inside the current facet
- detecting repeated current pages
- stopping when the next page has already been visited

Why Sioux needs it:

The old pagination loop used:

```python
current_url = page.url
```

The new retriever still needs that value, but it should get it from
`BrowserAccess`, not from a Playwright page.

## Required DOMElement Capabilities

### `get_attribute(name) -> str | None`

Needed for:

- reading facet `href` values
- reading vacancy card `href` values
- reading next-page `href` values

Why Sioux needs it:

The old adapter used `get_attribute("href")` for all link extraction.

### `get_text(selector=None) -> str`

Needed for:

- reading a facet name from `.filter-item-link-name`
- reading a facet count from `.filter-item-link-count`

Why Sioux needs it:

The old adapter read child text through:

```python
link.locator(".filter-item-link-name").inner_text()
link.locator(".filter-item-link-count").inner_text()
```

The new `DOMElement` method provides that without exposing Playwright locators.

## Capabilities Not Needed Yet

### Click-Based Pagination

Not needed for current Sioux behavior.

The old Sioux adapter set:

```python
is_click_next_control=lambda _element: False
```

So Sioux follows next-page URLs instead of clicking pagination controls.

### Exposing Playwright Page Or Locator

Not needed and should be avoided.

The new domain layer should not receive Playwright `Page`, `Locator`, browser,
or context objects. Those stay inside `PlaywrightBrowserAccess`.

### Multiple Active Pages

Not needed for the current Sioux flow.

The old adapter reused one Playwright page for entry, facet, and pagination
URLs. The new browser access can also own one active page for the full Sioux
retrieval session.

## Minimal Capability Set

The minimum browser access API for Sioux is:

```python
class BrowserAccess:
    def open_url(
        self,
        url: str,
        *,
        wait_for_selectors: Selectors = (),
        click_if_visible_selectors: Selectors = (),
    ) -> None: ...

    def find_elements(self, selector: Selector) -> list[DOMElement]: ...

    def current_url(self) -> str: ...
```

The minimum DOM element API for Sioux is:

```python
class DOMElement:
    def get_attribute(self, name: str) -> str | None: ...

    def get_text(self, selector: str | None = None) -> str: ...
```

This is enough to express the old Sioux behavior:

```text
open entry page
find facet elements
parse facet metadata
for each facet:
  open facet URL
  while facet is not complete:
    remember current URL
    find vacancy card elements
    extract vacancy hrefs
    stop if link limit is reached
    find next-page element
    stop if next page is missing or already visited
    open next-page URL
return deduplicated vacancy links
```
