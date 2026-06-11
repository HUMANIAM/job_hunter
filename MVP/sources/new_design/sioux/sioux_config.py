import re

SIOUX_ENTRY_URL = "https://vacancy.sioux.eu/"
SIOUX_RESULTS_READY_SELECTOR = "a.act-item-job-overview"
SIOUX_COOKIE_ACCEPT_SELECTOR = "input.cookieClose.cookieAccept"
SIOUX_JOB_URL_RE = re.compile(r"^https://vacancy\.sioux\.eu/vacancies/.+\.html$")
SIOUX_DISCIPLINE_FACET_SELECTOR = (
    "div.facets_item[data-type='functiegr'] a.filter-item-link"
)
SIOUX_NEXT_PAGE_SELECTOR = "div.overview-paging-controls a.paging-item-next"
