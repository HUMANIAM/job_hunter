from __future__ import annotations

from ui.tests.integration.dummy_http_server import DummyHttpServer


def main() -> None:
    print("creating server", flush=True)
    server = DummyHttpServer()
    print("calling close() without start()", flush=True)
    server.close()
    print("close() returned", flush=True)


if __name__ == "__main__":
    main()
