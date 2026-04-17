from dataclasses import dataclass
from typing import Literal, Optional, get_args


IntegrityKind = Literal["unique", "not_null", "foreign_key", "check", "other"]
ALLOWED_INTEGRITY_KINDS = set(get_args(IntegrityKind))


@dataclass(frozen=True)
class IntegrityViolationError(Exception):
    """Raised when a database write violates an integrity constraint."""

    operation: str
    kind: IntegrityKind
    entity: str
    field: Optional[str] = None
    detail: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in ALLOWED_INTEGRITY_KINDS:
            raise ValueError(f"Invalid integrity kind: {self.kind}")

    def __str__(self) -> str:
        parts = [self.operation, self.kind, self.entity]
        if self.field:
            parts.append(f"field={self.field}")
        return "IntegrityViolationError(" + ", ".join(parts) + ")"


@dataclass(frozen=True)
class StorageError(Exception):
    """Raised for unexpected persistence failures."""

    operation: str
    detail: Optional[str] = None

    def __str__(self) -> str:
        detail = f": {self.detail}" if self.detail else ""
        return f"storage error during {self.operation}{detail}"