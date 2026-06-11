# Vacancy Link Retrieval Abstraction

## Goal

Design a clear abstraction layer for retrieving vacancy links.

The layer must hide retrieval mechanics from callers. A caller should ask for
vacancy links for a client/company and should not know whether those links came
from an API, a rendered DOM page, pagination clicks, facets, Playwright, or an
HTTP library.

This abstraction is for vacancy link discovery only. Downloading vacancy page
content and normalizing downloaded HTML are separate concerns.

## Terms

- **IF**: Stable interface/contract that callers depend on.
- **Realization**: Concrete class that fulfills an IF.
- **Contract**: The promised behavior of an IF, including inputs, outputs,
  ordering, limit handling, and abstract error semantics.

## Design Principles

- Model domain capabilities, not implementation mechanisms.
- Keep interfaces small and justified by current needs.
- Depend on IFs, not concrete classes.
- Keep implementation data behind realizations.
- Do not leak API responses, DOM pages, selectors, request states, pagination
  controls, Playwright objects, or HTTP library errors through domain IFs.
- Abstract errors at the layer boundary.
- Optimize for the common workflow shared by API-based and DOM-based retrieval.

## Layer Overview

```text
CLI / Pipeline
  -> VacancySource IF
       -> VacancyLinkRetriever IF
            -> BrowserAccess IF
            -> HttpAccess IF
                 -> external frameworks
```

## IFs And Responsibilities

### VacancySource IF

Client-facing domain IF.

Responsibility:

- Represents one configured client/company vacancy source.
- Provides a stable API to retrieve vacancy links.
- Hides which retrieval mechanism is used.

Contract:

```text
get_vacancy_links(criteria) -> VacancyLinks
```

The returned links are vacancy detail page URLs. The IF does not return vacancy
content.

The caller must not receive implementation-specific data or errors.

### VacancyLinkRetriever IF

Internal domain IF used by `VacancySource` realizations.

Responsibility:

- Retrieves vacancy links using a source-specific realization.
- Applies source scope and filtering.
- Deduplicates links.
- Respects the requested limit.
- Provides stable ordering where practical.
- Reports failures using abstract retrieval errors.

Contract:

```text
retrieve_vacancy_links(criteria) -> VacancyLinks
```

This IF models the common behavior between API-based and DOM-based retrieval.
It must not expose API request state, raw responses, DOM pages, selectors, or
pagination controls.

### BrowserAccess IF

Mechanism IF for browser-based access.

Responsibility:

- Hide the concrete browser framework.
- Own browser/page lifecycle details needed for retrieval.
- Provide only the browser capabilities required by vacancy link retrieval.

This IF may be realized with Playwright today and another browser framework
later. It should not become a full wrapper around every browser framework API.

### HttpAccess IF

Mechanism IF for HTTP-based access.

Responsibility:

- Hide the concrete HTTP framework.
- Own request/session details needed for retrieval.
- Normalize HTTP/framework failures into abstract access errors.

This IF may be realized with `requests` today and another HTTP client later. It
should expose only the request capabilities required by vacancy link retrieval.

## Realization Relationships

Example API-based client:

```text
PhilipsVacancySource
  realizes VacancySource
  depends on VacancyLinkRetriever IF

PhilipsVacancyLinkRetriever
  realizes VacancyLinkRetriever
  depends on HttpAccess IF
```

Example DOM-based client:

```text
SiouxVacancySource
  realizes VacancySource
  depends on VacancyLinkRetriever IF

SiouxVacancyLinkRetriever
  realizes VacancyLinkRetriever
  depends on BrowserAccess IF
```

Framework realizations:

```text
PlaywrightBrowserAccess
  realizes BrowserAccess

RequestsHttpAccess
  realizes HttpAccess
```

## Shared Retrieval Workflow

Both API-based and DOM-based retrievers follow the same domain workflow:

```text
initialize source-specific retrieval
retrieve one listing page/batch
extract vacancy links
deduplicate
apply limit
decide whether more listing data exists
repeat until complete or stopped
return vacancy links
```

The mechanism differs, but the workflow and caller-facing result are the same.

## Out Of Scope For This Layer

- Downloading vacancy page HTML.
- Transforming downloaded HTML.
- Extracting structured job content.
- Ranking or evaluating vacancies.
- Exposing low-level browser or HTTP operations to the CLI/pipeline.

If a client needs downloaded HTML normalization, it should use a separate IF
from vacancy link retrieval.
