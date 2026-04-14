from enum import Enum


class Client(str, Enum):
    SIOUX = "sioux"
    ASML = "asml"
    DAF = "daf"


def parse_client(value: str) -> Client:
    normalized = value.strip().lower()
    try:
        return Client(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported client: {value!r}") from exc


def client_value(client: Client) -> str:
    return client.value
