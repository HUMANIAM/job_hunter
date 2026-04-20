from typing import Optional, TypeVar

from core.errors import NotFoundError

T = TypeVar("T")


def ensure_found(
    value: Optional[T],
    *,
    resource: str,
    lookup_field: str,
    lookup_value: object,
    operation: Optional[str] = None,
) -> T:
    if value is None:
        raise NotFoundError(
            resource=resource,
            lookup_field=lookup_field,
            lookup_value=lookup_value,
            operation=operation,
        )
    return value
