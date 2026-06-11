from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from enum import Enum

DEFAULT_HTTP_TIMEOUT_SECONDS = 30

@dataclass(frozen=True)
class HttpRequest:
    url: str
    headers: dict[str, str]
    body: dict[str, Any]
    timeout_seconds: int = DEFAULT_HTTP_TIMEOUT_SECONDS


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    content: dict[str, Any]


class HttpAccessFailureKind(str, Enum):
    UNAVAILABLE = "unavailable"  # e.g. timeout, connection error, TLS error.
    REJECTED = "rejected"  # e.g. 4xx or 5xx status code, forbidden, server error.
    INVALID_RESPONSE = "invalid_response"  # e.g. invalid or malformed JSON.
    OTHER = "other"  # Any failure that does not fit the common categories.


@dataclass(frozen=True)
class HttpAccessError(Exception):
    failure_kind: HttpAccessFailureKind
    status_code: int | None = None
    response_text: str | None = None


class HttpAccess(ABC):
    @abstractmethod
    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Perform an HTTP POST request.

        Args:
            request: HTTP request data needed by the access layer.

        Returns:
            The response content as an HttpResponse object.
        """
        pass
