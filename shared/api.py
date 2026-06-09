from __future__ import annotations

from typing import Any

import requests

from infra.logging import log


class ApiClient:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout_seconds = timeout_seconds

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any],
        error_prefix: str,
        log_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._session.post(
            url,
            headers=headers,
            json=json_body,
            timeout=self._timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            context = ""
            if log_context:
                context = " " + " ".join(
                    f"{key}={value}" for key, value in log_context.items()
                )

            log(
                f"{error_prefix}: request failed "
                f"status={response.status_code}"
                f"{context} "
                f"url={response.url}"
            )
            raise

        return response.json()
