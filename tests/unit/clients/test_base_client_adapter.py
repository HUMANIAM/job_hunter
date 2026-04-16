from __future__ import annotations

from clients.base import BaseClientAdapter


class _ConcreteAdapter(BaseClientAdapter):
    pass


def test_collect_job_links_requires_concrete_adapter_implementation() -> None:
    adapter = _ConcreteAdapter()

    try:
        adapter.collect_job_links(job_limit=3)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("expected NotImplementedError")
