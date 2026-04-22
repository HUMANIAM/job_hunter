from __future__ import annotations

import pytest
import requests

import ui.shared.api as api_module
from ui.tests.integration.dummy_http_server import run_dummy_http_server


class TestApiClient:
    @pytest.fixture(autouse=True)
    def _setup(self, patch_api_settings) -> None:
        self.api_settings = patch_api_settings(api_module)
        self.url_path = "/candidate-profiles"

    def test_get_json_sends_real_request_and_returns_json(
        self,
    ) -> None:
        with run_dummy_http_server(response_json={"ok": True}) as server:
            self.api_settings.BACKEND_BASE_URL = server.base_url
            session = requests.Session()
            session.headers.update({"X-Test-Header": "trace-123"})

            client = api_module.ApiClient(session=session)
            params = {"profile_id": 42, "tag": "python"}
            result = client.get_json(self.url_path, params=params,)

            request = server.get_received_request()
            headers = server.get_received_request_headers()

        assert result == {"ok": True}
        assert request.method == "GET"
        assert request.path == self.url_path
        assert request.query == {"profile_id": ["42"], "tag": ["python"]}
        assert headers["X-Test-Header"] == "trace-123"


    def test_api_get_json_raises_api_error_for_http_failure(self,) -> None:
        with run_dummy_http_server(response_status=500, response_json={"error": "boom"}) as server:
            self.api_settings.BACKEND_BASE_URL = server.base_url
            client = api_module.ApiClient()

            with pytest.raises(api_module.ApiError, match=r"GET .* failed: 500 Server Error"):
                client.get_json(self.url_path, params={"profile_id": 7})

            request = server.get_received_request()

        assert request.method == "GET"
        assert request.path == self.url_path
        assert request.query == {"profile_id": ["7"]}


    def test_api_client_get_json_raises_api_error_for_invalid_json(
        self,
    ) -> None:
        with run_dummy_http_server(response_body="not-json") as server:
            self.api_settings.BACKEND_BASE_URL = server.base_url
            client = api_module.ApiClient()

            with pytest.raises(api_module.ApiError, match=r"returned invalid JSON"):
                client.get_json(self.url_path, params={"profile_id": 9})

            request = server.get_received_request()

        assert request.method == "GET"
        assert request.path == self.url_path
        assert request.query == {"profile_id": ["9"]}
