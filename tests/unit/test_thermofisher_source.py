from __future__ import annotations

from sources.thermofisher import ThermoFisherSourceParser


class _FakePage:
    def __init__(self, html: str) -> None:
        self._html = html
        self.requested_urls: list[str] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout == 30000
        self.requested_urls.append(url)

    def wait_for_timeout(self, timeout_ms: int) -> None:
        assert timeout_ms == 500

    def content(self) -> str:
        return self._html


def test_fetch_raw_job_extracts_core_fields_from_workday_json_ld() -> None:
    html = """
    <html>
      <head>
        <meta name="title" property="og:title" content="Sr Assembler">
        <meta
          name="description"
          property="og:description"
          content="Build and assemble microscopes."
        >
        <script type="application/ld+json">
          {
            "@type": "JobPosting",
            "title": "Sr Assembler",
            "description": "Build and assemble microscopes for research teams.",
            "employmentType": "FULL_TIME",
            "jobLocationType": "TELECOMMUTE",
            "applicantLocationRequirements": {
              "@type": "Country",
              "name": "Netherlands"
            },
            "jobLocation": {
              "@type": "Place",
              "address": {
                "@type": "PostalAddress",
                "addressCountry": "Netherlands",
                "addressLocality": "Netherlands - Eindhoven - Achtseweg Noord 5"
              }
            },
            "identifier": {
              "@type": "PropertyValue",
              "value": "R-01269523"
            }
          }
        </script>
      </head>
      <body></body>
    </html>
    """
    page = _FakePage(html)

    job = ThermoFisherSourceParser().fetch_raw_job(
        page,
        "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/job/Eindhoven-Netherlands/Sr-Assembler_R-01269523",
        disciplines=["operations"],
    )

    assert job is not None
    assert job.job_id == "R-01269523"
    assert job.title == "Sr Assembler"
    assert job.url.endswith("Sr-Assembler_R-01269523")
    assert job.disciplines == ["operations"]
    assert job.location == "Eindhoven, Netherlands"
    assert job.country == "Netherlands"
    assert job.fulltime_parttime == "Full Time"
    assert job.remote_policy == "remote"
    assert job.description_text == "Build and assemble microscopes for research teams."
