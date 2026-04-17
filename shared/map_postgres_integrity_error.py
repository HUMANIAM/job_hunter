import re
from typing import Optional, cast

from sqlalchemy.exc import IntegrityError

from core.errors import (
    ALLOWED_INTEGRITY_KINDS,
    IntegrityKind,
    IntegrityViolationError,
)

_UNIQUE_DETAIL_PATTERN = re.compile(r"\((?P<column>[^)]+)\)=\(")

_SQLSTATE_TO_KIND = {
    "23505": "unique",
    "23502": "not_null",
    "23503": "foreign_key",
    "23514": "check",
}


def _get_diag_attr(orig: object, name: str) -> Optional[str]:
    diag = getattr(orig, "diag", None)
    if diag is None:
        return None
    value = getattr(diag, name, None)
    return value if isinstance(value, str) and value else None


def _extract_field_from_unique_detail(detail: str) -> Optional[str]:
    match = _UNIQUE_DETAIL_PATTERN.search(detail)
    if not match:
        return None

    raw = match.group("column").strip()
    # If PostgreSQL reports multiple columns, do not pretend it is one field.
    if "," in raw:
        return None
    return raw


def map_postgres_integrity_error(
    error: IntegrityError,
    *,
    operation: str,
    entity: str,
) -> IntegrityViolationError:
    orig = getattr(error, "orig", error)
    detail = str(orig)

    sqlstate = getattr(orig, "sqlstate", None) or _get_diag_attr(orig, "sqlstate")
    kind_str = _SQLSTATE_TO_KIND.get(sqlstate, "other")

    field: Optional[str] = None

    if kind_str in {"unique", "not_null"}:
        field = _get_diag_attr(orig, "column_name")

        # PostgreSQL often doesn't provide column_name for unique violations.
        if field is None and kind_str == "unique":
            field = _extract_field_from_unique_detail(detail)

    if kind_str not in ALLOWED_INTEGRITY_KINDS:
        kind_str = "other"
        field = None

    kind = cast(IntegrityKind, kind_str)

    return IntegrityViolationError(
        operation=operation,
        kind=kind,
        entity=entity,
        field=field,
        detail=detail,
    )
