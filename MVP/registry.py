from __future__ import annotations

from typing import Type

from MVP.base import BaseClientAdapter
from MVP.clients import Client
from MVP.sources.asml.adapter import AsmlClientAdapter
from MVP.sources.canon.adapter import CanonAPIListingAdapter
from MVP.sources.daf.adapter import DafClientAdapter
from MVP.sources.philips.adapter import PhilipsAPIListingAdapter
from MVP.sources.sioux.adapter import SiouxBrowserListingAdapter
from MVP.sources.vanderlande.adapter import VanderlandeClientAdapter


_CLIENT_ADAPTERS: dict[Client, Type[BaseClientAdapter]] = {
    Client.ASML: AsmlClientAdapter,
    Client.CANON: CanonAPIListingAdapter,
    Client.DAF: DafClientAdapter,
    Client.PHILIPS: PhilipsAPIListingAdapter,
    Client.SIOUX: SiouxBrowserListingAdapter,
    Client.VANDERLANDE: VanderlandeClientAdapter,
}


def get_client_adapter(client: Client) -> BaseClientAdapter:
    try:
        adapter_cls = _CLIENT_ADAPTERS[client]
    except KeyError as exc:
        raise ValueError(f"No adapter registered for client: {client}") from exc

    return adapter_cls()
