from __future__ import annotations

import json
import os
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


def render_template(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def require_env_value(name: str, *, error_context: str) -> str:
    value = os.environ.get(name)
    if value:
        return value

    raise RuntimeError(f"{name} is required for {error_context}")


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
                {"role": "user", "content": self._render_user_message(payload)},
            ],
            timeout=self._timeout_seconds,
        )

        message = completion.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise RuntimeError(f"{self._operation_name} refused the request: {refusal}")

        if message.parsed is None:
            raise RuntimeError(
                f"{self._operation_name} did not return parsed JSON output"
            )

        return message.parsed
