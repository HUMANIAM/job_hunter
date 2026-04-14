from __future__ import annotations

from typing import Type

from clients.base import BaseClientAdapter
from clients.clients import Client
from clients.sources.asml.adapter import AsmlClientAdapter
from clients.sources.canon.adapter import CanonClientAdapter
from clients.sources.daf.adapter import DafClientAdapter
from clients.sources.philips.adapter import PhilipsClientAdapter
from clients.sources.sioux.adapter import SiouxClientAdapter
from clients.sources.vanderlande.adapter import VanderlandeClientAdapter


_CLIENT_ADAPTERS: dict[Client, Type[BaseClientAdapter]] = {
    Client.ASML: AsmlClientAdapter,
    Client.CANON: CanonClientAdapter,
    Client.DAF: DafClientAdapter,
    Client.PHILIPS: PhilipsClientAdapter,
    Client.SIOUX: SiouxClientAdapter,
    Client.VANDERLANDE: VanderlandeClientAdapter,
}


def get_client_adapter(client: Client) -> BaseClientAdapter:
    try:
        adapter_cls = _CLIENT_ADAPTERS[client]
    except KeyError as exc:
        raise ValueError(f"No adapter registered for client: {client}") from exc

    return adapter_cls()
