from __future__ import annotations

from typing import Type

from clients.base import BaseClientAdapter
from clients.clients import Client
from clients.sources.asml.adapter import AsmlClientAdapter
from clients.sources.sioux.adapter import SiouxClientAdapter


_CLIENT_ADAPTERS: dict[Client, Type[BaseClientAdapter]] = {
    Client.ASML: AsmlClientAdapter,
    Client.SIOUX: SiouxClientAdapter,
}


def get_client_adapter(client: Client) -> BaseClientAdapter:
    try:
        adapter_cls = _CLIENT_ADAPTERS[client]
    except KeyError as exc:
        raise ValueError(f"No adapter registered for client: {client}") from exc

    return adapter_cls()
