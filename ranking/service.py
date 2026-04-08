# service.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Sequence

from ranking.evaluator import RankingResult, evaluate_job_match


@dataclass
class RankingBatchResult:
    results: list[dict[str, Any]]
    ranked_jobs: list[Any]


def _log_ranking(
    job: Any,
    ranking: RankingResult,
    *,
    index: int | None = None,
    log_message: Callable[[str], None] | None = None,
) -> None:
    if log_message is None:
        return

    rank_prefix = f"RANK [{index}] " if index is not None else "RANK "
    reason = ranking.rejection_reasons[0].reason if ranking.rejection_reasons else "none"
    log_message(
        f"{rank_prefix}'{job.title}' | "
        f"status={ranking.status} | "
        f"stage={ranking.decision_stage} | "
        f"reason={reason} | "
        f"score={ranking.score:.3f} | "
        f"skills={ranking.bucket_scores.skills:.3f} | "
        f"languages={ranking.bucket_scores.languages:.3f} | "
        f"protocols={ranking.bucket_scores.protocols:.3f} | "
        f"standards={ranking.bucket_scores.standards:.3f} | "
        f"domains={ranking.bucket_scores.domains:.3f} | "
        f"seniority={ranking.bucket_scores.seniority:.3f} | "
        f"years_experience={ranking.bucket_scores.years_experience:.3f}"
    )


def rank_job(
    candidate_profile: Any,
    job: Any,
    *,
    match_score_threshold: float = 0.6,
    index: int | None = None,
    log_message: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    ranking = evaluate_job_match(
        candidate_profile,
        job,
        match_score_threshold=match_score_threshold,
    )
    _log_ranking(
        job,
        ranking,
        index=index,
        log_message=log_message,
    )
    return asdict(ranking)


def rank_jobs(
    candidate_profile: Any,
    jobs: Sequence[Any],
    *,
    match_score_threshold: float = 0.6,
    log_message: Callable[[str], None] | None = None,
) -> RankingBatchResult:
    results: list[dict[str, Any]] = []
    ranked: list[tuple[Any, RankingResult]] = []

    for idx, job in enumerate(jobs, start=1):
        ranking = evaluate_job_match(
            candidate_profile,
            job,
            match_score_threshold=match_score_threshold,
        )
        ranked.append((job, ranking))
        _log_ranking(
            job,
            ranking,
            index=idx,
            log_message=log_message,
        )

    matches = [(job, ranking) for job, ranking in ranked if ranking.status == "match"]
    mismatches = [
        (job, ranking) for job, ranking in ranked if ranking.status == "mismatch"
    ]
    matches.sort(key=lambda item: item[1].score, reverse=True)

    for _, ranking in [*matches, *mismatches]:
        results.append(asdict(ranking))

    return RankingBatchResult(
        results=results,
        ranked_jobs=[job for job, _ in [*matches, *mismatches]],
    )
