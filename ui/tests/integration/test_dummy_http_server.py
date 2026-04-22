from __future__ import annotations

import requests

from ui.tests.integration.dummy_http_server import run_dummy_http_server


def test_dummy_http_server_captures_received_request_and_headers() -> None:
    with run_dummy_http_server(response_json={"ok": True}) as server:
        response = requests.post(
            server.url("/candidate-profiles?tag=python"),
            headers={"X-Trace-Id": "trace-123"},
            json={"uploaded_cv_id": 42},
            timeout=1.0,
        )

        request = server.get_received_request()
        headers = server.get_received_request_headers()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert request.method == "POST"
    assert request.path == "/candidate-profiles"
    assert request.query == {"tag": ["python"]}
    assert request.json() == {"uploaded_cv_id": 42}
    assert headers["X-Trace-Id"] == "trace-123"
    assert headers["Content-Type"].startswith("application/json")
