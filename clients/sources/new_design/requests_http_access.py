from __future__ import annotations

from types import TracebackType

import requests

from clients.sources.new_design import http_access as http
from infra.logging import log


class RequestsHttpAccessErrorMapper:
    def map_status_error(self, response: requests.Response) -> http.HttpAccessError:
        return http.HttpAccessError(
            failure_kind=http.HttpAccessFailureKind.REJECTED,
            status_code=response.status_code,
            response_text=response.text,
        )

    def map_exception_error(self, exc: Exception) -> http.HttpAccessError:
        if isinstance(exc, requests.HTTPError):
            response = exc.response
            if response is not None:
                return self.map_status_error(response)
            failure_kind = http.HttpAccessFailureKind.REJECTED
        elif isinstance(exc, ValueError):  # e.g. JSON decoding error
            failure_kind = http.HttpAccessFailureKind.INVALID_RESPONSE
        elif isinstance(exc, requests.RequestException):
            failure_kind = http.HttpAccessFailureKind.UNAVAILABLE
        else:
            failure_kind = http.HttpAccessFailureKind.OTHER

        return http.HttpAccessError(failure_kind=failure_kind)


class RequestsHttpAccess(http.HttpAccess):
    """Requests-based HTTP access.

    This class manages the requests session lifecycle. Callers should close
    this realization through context management or `close()`, and must not use
    or close the underlying session directly after handing it over.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        error_mapper: RequestsHttpAccessErrorMapper | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._error_mapper = error_mapper or RequestsHttpAccessErrorMapper()

    def __enter__(self) -> RequestsHttpAccess:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    def post(self, request: http.HttpRequest) -> http.HttpResponse:
        try:
            response = self._session.post(
                request.url,
                headers=request.headers,
                json=request.body,
                timeout=request.timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:
            access_error = self._error_mapper.map_exception_error(exc)
            log(
                "HTTP POST failed "
                f"kind={access_error.failure_kind} "
                f"status={access_error.status_code} "
                f"url={request.url} "
                f"error={exc}"
            )
            raise access_error from exc

        try:
            content = response.json()
        except ValueError as exc:
            access_error = self._error_mapper.map_exception_error(exc)
            log(
                "HTTP POST failed "
                f"kind={access_error.failure_kind} "
                f"url={request.url} "
                f"error={exc}"
            )
            raise access_error from exc

        return http.HttpResponse(
            status_code=response.status_code,
            content=content,
        )

    def get(self, request: http.HttpRequest) -> http.HttpResponse:
        try:
            response = self._session.get(
                request.url,
                headers=request.headers,
                timeout=request.timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:
            access_error = self._error_mapper.map_exception_error(exc)
            log(
                "HTTP GET failed "
                f"kind={access_error.failure_kind} "
                f"status={access_error.status_code} "
                f"url={request.url} "
                f"error={exc}"
            )
            raise access_error from exc

        return http.HttpResponse(
            status_code=response.status_code,
            content=response.text,
        )
