from __future__ import annotations

from shared.html import (
    extract_canonical_url,
    extract_meta_content,
    find_jsonld_nodes_by_type,
)


def test_extract_meta_content_unescapes_until_stable() -> None:
    raw_html = (
        "<html><head>"
        '<meta property="og:title" content="S&amp;amp;OE Manager"/>'
        "</head></html>"
    )

    assert extract_meta_content(raw_html, property_name="og:title") == "S&OE Manager"


def test_extract_canonical_url_returns_link_href() -> None:
    raw_html = (
        "<html><head>"
        '<link rel="canonical" href="https://example.com/job/123"/>'
        "</head></html>"
    )

    assert extract_canonical_url(raw_html) == "https://example.com/job/123"


def test_find_jsonld_nodes_by_type_returns_unescaped_job_postings() -> None:
    raw_html = """
    <html><head>
      <script type="application/ld+json">
        {
          "@context": "http://schema.org",
          "@type": "JobPosting",
          "title": "S&amp;OE Manager"
        }
      </script>
    </head></html>
    """

    nodes = find_jsonld_nodes_by_type(raw_html, "JobPosting")

    assert nodes == [
        {
            "@context": "http://schema.org",
            "@type": "JobPosting",
            "title": "S&OE Manager",
        }
    ]
