from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable, Sequence

from ranking.evaluator import evaluate_job


@dataclass
class RankingBatchResult:
    evaluated_jobs: list[dict[str, Any]]
    kept_jobs: list[Any]


def _serialize_job(job: Any) -> dict[str, Any]:
    if is_dataclass(job):
        return asdict(job)
    if hasattr(job, "__dict__"):
        return dict(vars(job))
    raise TypeError(f"unsupported job type for ranking serialization: {type(job)!r}")


def evaluate_jobs(
    jobs: Sequence[Any],
    *,
    log_message: Callable[[str], None] | None = None,
) -> RankingBatchResult:
    evaluated_jobs: list[dict[str, Any]] = []
    kept_jobs: list[Any] = []

    for idx, job in enumerate(jobs, start=1):
        evaluation = evaluate_job(job)

        if log_message is not None:
            if evaluation["decision"] == "keep":
                log_message(
                    f"KEEP [{idx}] '{job.title}' | "
                    f"reason={evaluation['reason']} | "
                    f"title_hits={evaluation['title_hits']} | "
                    f"description_hits={evaluation['description_hits']}"
                )
            else:
                log_message(
                    f"SKIP [{idx}] '{job.title}' | "
                    f"reason={evaluation['reason']} | "
                    f"skip_hits={evaluation['skip_hits']} | "
                    f"description_hits={evaluation['description_hits']}"
                )

        if evaluation["decision"] == "keep":
            kept_jobs.append(job)

        job_dict = _serialize_job(job)
        job_dict["decision"] = evaluation["decision"]
        job_dict["reason"] = evaluation["reason"]
        job_dict["skip_hits"] = evaluation["skip_hits"]
        job_dict["title_hits"] = evaluation["title_hits"]
        job_dict["description_hits"] = evaluation["description_hits"]
        evaluated_jobs.append(job_dict)

    return RankingBatchResult(
        evaluated_jobs=evaluated_jobs,
        kept_jobs=kept_jobs,
    )
