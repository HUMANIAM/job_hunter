from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Lock, Thread
from typing import Any, Iterator, Mapping
from urllib.parse import parse_qs, urlparse


def _build_response_payload(
    *,
    response_json: Any | None,
    response_body: bytes | str | None,
    response_headers: Mapping[str, str] | None,
) -> tuple[bytes, dict[str, str]]:
    if response_json is not None and response_body is not None:
        raise ValueError("Pass either response_json or response_body, not both")

    headers = dict(response_headers or {})

    if response_json is not None:
        headers.setdefault("Content-Type", "application/json")
        return json.dumps(response_json).encode("utf-8"), headers

    if response_body is None:
        return b"", headers

    if isinstance(response_body, str):
        return response_body.encode("utf-8"), headers

    return response_body, headers


@dataclass(frozen=True)
class ReceivedRequest:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: bytes

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding)

    def json(self) -> Any:
        return json.loads(self.text())


class DummyHttpServer:
    HOST = "127.0.0.1"
    PORT = 58123

    def __init__(
        self,
        *,
        response_status: int = 200,
        response_json: Any | None = None,
        response_body: bytes | str | None = None,
        response_headers: Mapping[str, str] | None = None,
    ) -> None:
        body, headers = _build_response_payload(
            response_json=response_json,
            response_body=response_body,
            response_headers=response_headers,
        )

        self._response_status = response_status
        self._response_body = body
        self._response_headers = headers
        self._requests: list[ReceivedRequest] = []  # Recorded requests in arrival order.
        self._requests_lock = Lock()  # Guards request list updates from handler threads.
        self._request_received = Event()  # Signals that at least one request was captured.
        self._thread: Thread | None = None  # Background server thread after start().
        self._server = self._build_server()

    def _build_server(self) -> ThreadingHTTPServer:
        outer = self

        class RequestHandler(BaseHTTPRequestHandler):
            def do_DELETE(self) -> None:
                self._handle_request()

            def do_GET(self) -> None:
                self._handle_request()

            def do_PATCH(self) -> None:
                self._handle_request()

            def do_POST(self) -> None:
                self._handle_request()

            def do_PUT(self) -> None:
                self._handle_request()

            def log_message(self, _format: str, *args: object) -> None:
                return

            def _handle_request(self) -> None:
                parsed = urlparse(self.path)
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length) if content_length else b""

                outer._record_request(
                    ReceivedRequest(
                        method=self.command,
                        path=parsed.path,
                        query=parse_qs(parsed.query, keep_blank_values=True),
                        headers={key: value for key, value in self.headers.items()},
                        body=body,
                    )
                )

                self.send_response(outer._response_status)
                for key, value in outer._response_headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(outer._response_body)))
                self.end_headers()
                if outer._response_body:
                    self.wfile.write(outer._response_body)

        return ThreadingHTTPServer((self.HOST, self.PORT), RequestHandler)

    @property
    def base_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"

    def url(self, path: str = "/") -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def start(self) -> DummyHttpServer:
        if self._thread is not None:
            return self

        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def close(self) -> None:
        if self._thread is None:
            self._server.server_close()
            return

        self._server.shutdown()
        self._thread.join()
        self._server.server_close()

    def _record_request(self, request: ReceivedRequest) -> None:
        with self._requests_lock:
            self._requests.append(request)
        self._request_received.set()

    def get_received_request(
        self,
        *,
        timeout: float = 1.0,
        index: int = -1,
    ) -> ReceivedRequest:
        if not self._request_received.wait(timeout=timeout):
            raise TimeoutError("No request was received before the timeout elapsed")

        with self._requests_lock:
            if not self._requests:
                raise TimeoutError("No request was recorded")
            return self._requests[index]

    def get_received_request_headers(
        self,
        *,
        timeout: float = 1.0,
        index: int = -1,
    ) -> dict[str, str]:
        return dict(self.get_received_request(timeout=timeout, index=index).headers)


@contextmanager
def run_dummy_http_server(
    *,
    response_status: int = 200,
    response_json: Any | None = None,
    response_body: bytes | str | None = None,
    response_headers: Mapping[str, str] | None = None,
) -> Iterator[DummyHttpServer]:
    server = DummyHttpServer(
        response_status=response_status,
        response_json=response_json,
        response_body=response_body,
        response_headers=response_headers,
    ).start()
    try:
        yield server
    finally:
        server.close()
