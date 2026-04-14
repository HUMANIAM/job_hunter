from __future__ import annotations


__all__ = ["VanderlandeClientAdapter"]


def __getattr__(name: str) -> object:
    if name == "VanderlandeClientAdapter":
        from clients.sources.vanderlande.adapter import VanderlandeClientAdapter

        return VanderlandeClientAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
