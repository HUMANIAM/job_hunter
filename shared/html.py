from __future__ import annotations

import html
import json
import re
from typing import Any, Iterable


JSONLD_SCRIPT_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_ATTRIBUTE_RE = re.compile(
    r"([^\s=/>]+)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)",
    re.IGNORECASE | re.DOTALL,
)


def html_unescape(value: str) -> str:
    current = value
    while True:
        unescaped = html.unescape(current)
        if unescaped == current:
            return unescaped
        current = unescaped


def normalize_inline_text(value: str) -> str:
    return re.sub(r"\s+", " ", html_unescape(value)).strip()


def extract_tag_attributes(raw_tag: str) -> dict[str, str]:
    attributes: dict[str, str] = {}

    for name, raw_value in _ATTRIBUTE_RE.findall(raw_tag):
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        attributes[name.lower()] = html_unescape(value)

    return attributes


def iter_jsonld_blocks(raw_html: str) -> Iterable[Any]:
    for match in JSONLD_SCRIPT_RE.finditer(raw_html):
        raw_block = match.group(1).strip()
        if not raw_block:
            continue
        yield json.loads(raw_block)


def _jsonld_node_matches_type(node: Any, type_name: str) -> bool:
    if not isinstance(node, dict):
        return False

    node_type = node.get("@type")
    if isinstance(node_type, list):
        return type_name in node_type
    return node_type == type_name


def _find_jsonld_nodes_by_type(node: Any, type_name: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if isinstance(node, dict):
        if _jsonld_node_matches_type(node, type_name):
            results.append(node)
        for value in node.values():
            results.extend(_find_jsonld_nodes_by_type(value, type_name))
    elif isinstance(node, list):
        for item in node:
            results.extend(_find_jsonld_nodes_by_type(item, type_name))

    return results


def _html_unescape_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return html_unescape(value)
    if isinstance(value, list):
        return [_html_unescape_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _html_unescape_json_value(item_value)
            for key, item_value in value.items()
        }
    return value


def find_jsonld_nodes_by_type(raw_html: str, type_name: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for block in iter_jsonld_blocks(raw_html):
        results.extend(_find_jsonld_nodes_by_type(block, type_name))

    return [_html_unescape_json_value(item) for item in results]


def extract_meta_content(
    raw_html: str,
    *,
    property_name: str | None = None,
    name: str | None = None,
) -> str | None:
    if (property_name is None) == (name is None):
        raise ValueError("provide exactly one of property_name or name")

    lookup_key = "property" if property_name is not None else "name"
    lookup_value = property_name if property_name is not None else name
    assert lookup_value is not None

    for raw_tag in _META_TAG_RE.findall(raw_html):
        attributes = extract_tag_attributes(raw_tag)
        if attributes.get(lookup_key) != lookup_value:
            continue
        content = attributes.get("content")
        if content:
            return normalize_inline_text(content)

    return None


def extract_canonical_url(raw_html: str) -> str | None:
    for raw_tag in _LINK_TAG_RE.findall(raw_html):
        attributes = extract_tag_attributes(raw_tag)
        if attributes.get("rel") != "canonical":
            continue
        href = attributes.get("href")
        if href:
            return normalize_inline_text(href)
    return None


__all__ = [
    "JSONLD_SCRIPT_RE",
    "extract_canonical_url",
    "extract_meta_content",
    "extract_tag_attributes",
    "find_jsonld_nodes_by_type",
    "html_unescape",
    "iter_jsonld_blocks",
    "normalize_inline_text",
]
