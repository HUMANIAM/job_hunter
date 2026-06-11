from __future__ import annotations

from typing import Any

import pytest
import requests

from clients.sources.new_design import http_access as http
from clients.sources.new_design.requests_http_access import RequestsHttpAccess


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        json_content: dict[str, Any] | None = None,
        status_error: requests.HTTPError | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._json_content = json_content or {}
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def json(self) -> dict[str, Any]:
        return self._json_content


class FakeSession:
    def __init__(
        self,
        *,
        get_response: FakeResponse | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self._get_response = get_response
        self._get_error = get_error
        self.get_calls: list[dict[str, Any]] = []
        self.closed = False

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        self.get_calls.append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if self._get_error is not None:
            raise self._get_error

        if self._get_response is None:
            raise AssertionError("GET response is not configured")

        return self._get_response

    def close(self) -> None:
        self.closed = True


def test_get_returns_response_text_content() -> None:
    session = FakeSession(
        get_response=FakeResponse(
            status_code=200,
            text="<html>job</html>",
        )
    )
    access = RequestsHttpAccess(session=session)

    response = access.get(
        http.HttpRequest(
            url="https://example.test/job",
            headers={"Accept": "text/html"},
            body={},
            timeout_seconds=12,
        )
    )

    assert response == http.HttpResponse(
        status_code=200,
        content="<html>job</html>",
    )
    assert session.get_calls == [
        {
            "url": "https://example.test/job",
            "headers": {"Accept": "text/html"},
            "timeout": 12,
        }
    ]


def test_get_maps_status_errors() -> None:
    response = FakeResponse(
        status_code=403,
        text="forbidden",
    )
    status_error = requests.HTTPError("403 forbidden", response=response)
    response = FakeResponse(
        status_code=403,
        text="forbidden",
        status_error=status_error,
    )
    session = FakeSession(get_response=response)
    access = RequestsHttpAccess(session=session)

    with pytest.raises(http.HttpAccessError) as exc_info:
        access.get(
            http.HttpRequest(
                url="https://example.test/job",
                headers={},
                body={},
            )
        )

    assert exc_info.value.failure_kind == http.HttpAccessFailureKind.REJECTED
    assert exc_info.value.status_code == 403
    assert exc_info.value.response_text == "forbidden"


def test_get_maps_request_errors() -> None:
    session = FakeSession(get_error=requests.Timeout("timed out"))
    access = RequestsHttpAccess(session=session)

    with pytest.raises(http.HttpAccessError) as exc_info:
        access.get(
            http.HttpRequest(
                url="https://example.test/job",
                headers={},
                body={},
            )
        )

    assert exc_info.value.failure_kind == http.HttpAccessFailureKind.UNAVAILABLE
