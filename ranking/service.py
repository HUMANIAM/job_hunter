# service.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Sequence

from ranking.evaluator import RankingResult, evaluate_job_match


@dataclass
class RankingBatchResult:
    results: list[dict[str, Any]]
    ranked_jobs: list[Any]


def rank_jobs(
    candidate_profile: Any,
    jobs: Sequence[Any],
    *,
    log_message: Callable[[str], None] | None = None,
) -> RankingBatchResult:
    results: list[dict[str, Any]] = []
    ranked: list[tuple[Any, RankingResult]] = []

    for idx, job in enumerate(jobs, start=1):
        ranking = evaluate_job_match(candidate_profile, job)
        ranked.append((job, ranking))

        if log_message is not None:
            log_message(
                f"RANK [{idx}] '{job.title}' | "
                f"score={ranking.score:.3f} | "
                f"skills={ranking.bucket_scores.skills:.3f} | "
                f"languages={ranking.bucket_scores.languages:.3f} | "
                f"protocols={ranking.bucket_scores.protocols:.3f} | "
                f"standards={ranking.bucket_scores.standards:.3f} | "
                f"domains={ranking.bucket_scores.domains:.3f} | "
                f"seniority={ranking.bucket_scores.seniority:.3f} | "
                f"years_experience={ranking.bucket_scores.years_experience:.3f}"
            )

    ranked.sort(key=lambda item: item[1].score, reverse=True)

    for _, ranking in ranked:
        results.append(asdict(ranking))

    return RankingBatchResult(
        results=results,
        ranked_jobs=[job for job, _ in ranked],
    )
