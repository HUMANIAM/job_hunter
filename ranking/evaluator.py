from __future__ import annotations

import re
from typing import Iterable, Protocol


class EvaluatableJob(Protocol):
    title: str | None
    description_text: str | None


SKIP_TITLE_KEYWORDS = [
    "intern",
    "internship",
    "trainee",
    "graduate",
    "thesis",
    "recruiter",
    "talent acquisition",
    "hr",
    "human resources",
    "payroll",
    "compensation",
    "benefits",
    "people partner",
    "finance",
    "financial",
    "controller",
    "accounting",
    "tax",
    "treasury",
    "audit",
    "procurement",
    "purchasing",
    "buyer",
    "sourcing",
    "commodity manager",
    "supply chain",
    "logistics",
    "warehouse",
    "planner",
    "marketing",
    "brand",
    "communications",
    "communication",
    "public relations",
    "content specialist",
    "sales",
    "account manager",
    "business development",
    "commercial",
    "legal",
    "counsel",
    "compliance",
    "privacy officer",
    "facility",
    "facilities",
    "real estate",
    "workplace services",
    "customer support",
    "service desk",
    "helpdesk",
    "administrative",
    "administrator",
    "office manager",
    "operator",
    "technician",
    "assembler",
    "manufacturing associate",
]

KEEP_KEYWORDS = [
    "c++",
    "python",
    "software engineer",
    "software designer",
    "embedded",
    "firmware",
    "control",
    "controls",
    "machine control",
    "real-time",
    "rtos",
    "linux",
    "system software",
    "systems engineering",
    "mechatronics software",
    "automation",
    "robotics",
    "computer vision",
    "algorithm",
    "performance",
    "high-tech",
    "signal processing",
    "image processing",
    "ml",
    "machine learning",
    "inference",
]

LOW_SIGNAL_DESCRIPTION_KEYWORDS = {
    "control",
    "controls",
    "performance",
    "high-tech",
}


def compile_keyword_patterns(keywords: Iterable[str]) -> tuple[re.Pattern[str], ...]:
    patterns: list[re.Pattern[str]] = []
    for keyword in keywords:
        escaped = re.escape(keyword.lower())
        patterns.append(re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"))
    return tuple(patterns)


SKIP_TITLE_PATTERNS = compile_keyword_patterns(SKIP_TITLE_KEYWORDS)
KEEP_PATTERNS = compile_keyword_patterns(KEEP_KEYWORDS)


def matched_keywords(
    text: str,
    keywords: list[str],
    patterns: Iterable[re.Pattern[str]],
) -> list[str]:
    normalized_text = text.lower()
    return [
        keyword
        for keyword, pattern in zip(keywords, patterns)
        if pattern.search(normalized_text)
    ]


def evaluate_job(job: EvaluatableJob) -> dict:
    title = job.title or ""
    description = job.description_text or ""

    title_hits = matched_keywords(title, KEEP_KEYWORDS, KEEP_PATTERNS)
    if title_hits:
        return {
            "decision": "keep",
            "reason": "title_keep_match",
            "skip_hits": [],
            "title_hits": title_hits,
            "description_hits": [],
        }

    skip_hits = matched_keywords(title, SKIP_TITLE_KEYWORDS, SKIP_TITLE_PATTERNS)
    if skip_hits:
        return {
            "decision": "skip",
            "reason": "skip_title_keywords",
            "skip_hits": skip_hits,
            "title_hits": [],
            "description_hits": [],
        }

    description_hits_all = matched_keywords(description, KEEP_KEYWORDS, KEEP_PATTERNS)
    description_hits = [
        keyword
        for keyword in description_hits_all
        if keyword not in LOW_SIGNAL_DESCRIPTION_KEYWORDS
    ]

    if len(description_hits) >= 2:
        return {
            "decision": "keep",
            "reason": "description_keep_match",
            "skip_hits": [],
            "title_hits": [],
            "description_hits": description_hits,
        }

    return {
        "decision": "skip",
        "reason": "insufficient_keep_signal",
        "skip_hits": [],
        "title_hits": [],
        "description_hits": description_hits,
    }
