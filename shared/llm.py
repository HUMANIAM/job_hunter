from __future__ import annotations

import json
import math
import sys
import traceback
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from openai import OpenAI
from pydantic import BaseModel

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


@lru_cache(maxsize=None)
def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=None)
def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _truncate_text(value: str, *, max_chars: int = 4000) -> str:
    if len(value) <= max_chars:
        return value
    truncated_chars = len(value) - max_chars
    return f"{value[:max_chars]}... <truncated {truncated_chars} chars>"


def _make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return repr(value)

    if isinstance(value, dict):
        return {
            str(key): _make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]

    return repr(value)


def _emit_failure_diagnostics(
    *,
    operation_name: str,
    model: str,
    response_format: type[BaseModel],
    timeout_seconds: float,
    temperature: float,
    max_completion_tokens: int,
    system_message: str,
    user_message: str | None,
    payload: Any,
    error: Exception,
) -> None:
    request_preview = {
        "model": model,
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
        "timeout_seconds": timeout_seconds,
        "response_format": response_format.__name__,
        "system_message_length": len(system_message),
        "system_message_preview": _truncate_text(system_message),
        "user_message_length": len(user_message) if user_message is not None else None,
        "user_message_preview": (
            _truncate_text(user_message) if user_message is not None else None
        ),
        "payload_type": type(payload).__name__,
        "payload_preview": _truncate_text(repr(_make_json_safe(payload))),
    }

    strict_json_request = {
        "model": model,
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
        "timeout": timeout_seconds,
        "messages": [
            {"role": "system", "content": system_message},
            {
                "role": "user",
                "content": user_message,
            },
        ],
    }
    try:
        json.dumps(strict_json_request, allow_nan=False)
        request_preview["strict_json_serializable"] = True
    except (TypeError, ValueError) as strict_error:
        request_preview["strict_json_serializable"] = False
        request_preview["strict_json_error"] = str(strict_error)

    exception_details: dict[str, Any] = {
        "exception_type": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc(),
    }

    status_code = getattr(error, "status_code", None)
    if status_code is not None:
        exception_details["status_code"] = status_code

    body = getattr(error, "body", None)
    if body is not None:
        exception_details["body"] = _make_json_safe(body)

    response = getattr(error, "response", None)
    if response is not None:
        response_status = getattr(response, "status_code", None)
        if response_status is not None:
            exception_details["response_status_code"] = response_status

        response_text = getattr(response, "text", None)
        if response_text:
            exception_details["response_text"] = _truncate_text(response_text)

        response_json = None
        json_loader = getattr(response, "json", None)
        if callable(json_loader):
            try:
                response_json = json_loader()
            except Exception as response_json_error:
                exception_details["response_json_error"] = str(response_json_error)
        if response_json is not None:
            exception_details["response_json"] = _make_json_safe(response_json)

    diagnostics = {
        "operation_name": operation_name,
        "request": request_preview,
        "exception": exception_details,
    }
    sys.stderr.write("OpenAIStructuredExtractor request failed\n")
    sys.stderr.write(json.dumps(diagnostics, indent=2, ensure_ascii=True) + "\n")


def render_template(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered

def _decode_json_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def resolve_json_schema_node(
    schema_node: dict[str, Any],
    root_schema: dict[str, Any],
) -> dict[str, Any]:
    if "$ref" not in schema_node:
        return schema_node

    ref = schema_node["$ref"]
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema ref: {ref}")

    resolved_node: Any = root_schema
    for token in ref[2:].split("/"):
        resolved_node = resolved_node[_decode_json_pointer_token(token)]

    resolved_schema = resolve_json_schema_node(resolved_node, root_schema)
    if len(schema_node) == 1:
        return resolved_schema

    merged_schema = dict(resolved_schema)
    merged_schema.update(
        {key: value for key, value in schema_node.items() if key != "$ref"}
    )
    return merged_schema


def build_json_schema_example(
    schema_node: dict[str, Any],
    root_schema: dict[str, Any],
) -> Any:
    resolved_schema = resolve_json_schema_node(schema_node, root_schema)
    if "enum" in resolved_schema:
        return " | ".join(
            "null" if value is None else str(value)
            for value in resolved_schema["enum"]
        )

    schema_type = resolved_schema.get("type")
    if schema_type == "object":
        return {
            key: build_json_schema_example(value, root_schema)
            for key, value in resolved_schema.get("properties", {}).items()
        }

    if schema_type == "array":
        return [build_json_schema_example(resolved_schema["items"], root_schema)]

    if schema_type == "string":
        return "string"
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0.0
    if schema_type == "boolean":
        return False

    if isinstance(schema_type, list) and "null" in schema_type:
        return None

    raise ValueError(f"unsupported schema node for prompt example: {resolved_schema}")


class OpenAIStructuredExtractor(Generic[StructuredModelT]):
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str,
        response_format: type[StructuredModelT],
        system_message: str,
        render_user_message: Callable[[Any], str],
        operation_name: str,
        timeout_seconds: float = 60.0,
        temperature: float = 0.0,
        max_completion_tokens: int = 1400,
    ) -> None:
        self._client = client
        self._model = model
        self._response_format = response_format
        self._system_message = system_message
        self._render_user_message = render_user_message
        self._operation_name = operation_name
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_completion_tokens = max_completion_tokens

    def extract(self, payload: Any) -> StructuredModelT:
        user_message: str | None = None
        try:
            user_message = self._render_user_message(payload)
            completion = self._client.chat.completions.parse(
                model=self._model,
                n=1,
                temperature=self._temperature,
                presence_penalty=0,
                frequency_penalty=0,
                max_completion_tokens=self._max_completion_tokens,
                store=False,
                response_format=self._response_format,
                messages=[
                    {"role": "system", "content": self._system_message},
                    {"role": "user", "content": user_message},
                ],
                timeout=self._timeout_seconds,
            )
        except Exception as error:
            _emit_failure_diagnostics(
                operation_name=self._operation_name,
                model=self._model,
                response_format=self._response_format,
                timeout_seconds=self._timeout_seconds,
                temperature=self._temperature,
                max_completion_tokens=self._max_completion_tokens,
                system_message=self._system_message,
                user_message=user_message,
                payload=payload,
                error=error,
            )
            raise

        message = completion.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise RuntimeError(f"{self._operation_name} refused the request: {refusal}")

        if message.parsed is None:
            raise RuntimeError(
                f"{self._operation_name} did not return parsed JSON output"
            )

        return message.parsed
