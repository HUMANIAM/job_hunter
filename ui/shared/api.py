from __future__ import annotations

from typing import Mapping
from urllib.parse import urljoin

import requests

from ..settings import get_settings


class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, *, session: requests.Session | None = None) -> None:
        settings = get_settings()
        self._session = session or requests.Session()
        self._base_url = settings.BACKEND_BASE_URL.rstrip("/") + "/"
        self._timeout = settings.BACKEND_TIMEOUT_SECONDS

    def _build_url(self, path: str) -> str:
        return urljoin(self._base_url, path.lstrip("/"))

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> object:
        url = self._build_url(path)

        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ApiError(f"GET {url} failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(f"GET {url} returned invalid JSON") from exc
