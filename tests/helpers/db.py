from __future__ import annotations

from typing import Mapping, Sequence, Type, TypeVar

from sqlmodel import Session, select

ModelT = TypeVar("ModelT")


def add_record(session: Session, record: ModelT) -> ModelT:
    """Add one record to the current session and flush it."""
    session.add(record)
    session.flush()
    return record


def select_where_in(
    session: Session,
    entity_type: Type[ModelT],
    conditions: Mapping[str, Sequence[object]],
) -> list[ModelT]:
    """Select rows where each provided field matches any value in its list."""
    statement = select(entity_type)

    for field_name, values in conditions.items():
        candidate_values = list(values)
        if not candidate_values:
            return []

        if not hasattr(entity_type, field_name):
            raise ValueError(
                f"{entity_type.__name__} has no field named {field_name!r}"
            )

        statement = statement.where(
            getattr(entity_type, field_name).in_(candidate_values)
        )

    return list(session.exec(statement).all())
