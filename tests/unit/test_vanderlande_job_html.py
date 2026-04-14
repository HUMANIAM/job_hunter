from __future__ import annotations

from clients.sources.vanderlande.job_html import (
    extract_vanderlande_job_posting,
    is_vanderlande_workday_job_html,
    render_vanderlande_job_html,
)


_RAW_VANDERLANDE_HTML = """
<html lang="en-US"><head>
  <link rel="canonical" href="https://vanderlande.wd3.myworkdayjobs.com/nl-NL/careers/job/Veghel/S-OE-Manager_JR36282">
  <meta property="og:title" content="S&amp;amp;OE Manager">
  <meta property="og:description" content="Job Title S&amp;amp;OE Manager Job Description Sales &amp;amp; Operations Execution (S&amp;amp;OE) Manager Corporate Planning | Veghel, Netherlands About Vanderlande Vanderlande is headquartered in Veghel. What you'll do Define and maintain corporate standards.">
  <script type="application/ld+json">
    {
      "@context": "http://schema.org",
      "@type": "JobPosting",
      "title": "S&amp;OE Manager",
      "description": "Job Title S&amp;OE Manager Job Description Sales &amp; Operations Execution (S&amp;OE) Manager Corporate Planning | Veghel, Netherlands About Vanderlande Vanderlande is headquartered in Veghel. What you'll do Define and maintain corporate standards.",
      "datePosted": "2026-04-09",
      "validThrough": "2026-05-29",
      "employmentType": "FULL_TIME",
      "identifier": {
        "@type": "PropertyValue",
        "name": "S&amp;OE Manager",
        "value": "JR36282"
      },
      "hiringOrganization": {
        "@type": "Organization",
        "name": "Vanderlande Industries B.V."
      },
      "jobLocation": {
        "@type": "Place",
        "address": {
          "@type": "PostalAddress",
          "addressLocality": "Veghel",
          "addressCountry": "Nederland"
        }
      }
    }
  </script>
</head><body><div id="root"></div></body></html>
"""


def test_detects_vanderlande_workday_html() -> None:
    assert is_vanderlande_workday_job_html(_RAW_VANDERLANDE_HTML) is True


def test_extract_vanderlande_job_posting_uses_jobposting_payload() -> None:
    posting = extract_vanderlande_job_posting(_RAW_VANDERLANDE_HTML)

    assert posting is not None
    assert posting.title == "S&OE Manager"
    assert posting.job_id == "JR36282"
    assert posting.company_name == "Vanderlande Industries B.V."
    assert posting.location_label == "Veghel, Nederland"
    assert posting.employment_type == "FULL_TIME"
    assert posting.date_posted == "2026-04-09"
    assert posting.valid_through == "2026-05-29"


def test_render_vanderlande_job_html_keeps_only_relevant_payload() -> None:
    rendered = render_vanderlande_job_html(_RAW_VANDERLANDE_HTML)

    assert rendered == (
        "S&OE Manager",
        "<html>\n"
        "<head>\n"
        "<title>S&amp;OE Manager</title>\n"
        "</head>\n"
        "<body>\n"
        "<h1>S&amp;OE Manager</h1>\n"
        "<p>Canonical URL: https://vanderlande.wd3.myworkdayjobs.com/nl-NL/careers/job/Veghel/S-OE-Manager_JR36282</p>\n"
        "<p>Job ID: JR36282</p>\n"
        "<p>Company: Vanderlande Industries B.V.</p>\n"
        "<p>Location: Veghel, Nederland</p>\n"
        "<p>Employment Type: FULL_TIME</p>\n"
        "<p>Date Posted: 2026-04-09</p>\n"
        "<p>Valid Through: 2026-05-29</p>\n"
        "<h2>Job Description</h2>\n"
        "<p>Sales &amp; Operations Execution (S&amp;OE) Manager Corporate Planning | Veghel, Netherlands</p>\n"
        "<h2>About Vanderlande</h2>\n"
        "<p>Vanderlande is headquartered in Veghel.</p>\n"
        "<h2>What you&#x27;ll do</h2>\n"
        "<p>Define and maintain corporate standards.</p>\n"
        "</body>\n"
        "</html>",
    )
