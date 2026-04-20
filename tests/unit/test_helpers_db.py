from __future__ import annotations

from typing import Optional

import pytest
from sqlmodel import Field, SQLModel, Session, create_engine

from tests.helpers.db import add_record, select_where_in


class SelectWhereInItem(SQLModel, table=True):
    __tablename__ = "test_select_where_in_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    group: str
    status: str


@pytest.fixture
def sqlite_session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[SelectWhereInItem.__table__])
    with Session(engine) as session:
        yield session


def test_select_where_in_filters_by_single_field(sqlite_session: Session) -> None:
    sqlite_session.add_all(
        [
            SelectWhereInItem(group="a", status="active"),
            SelectWhereInItem(group="a", status="inactive"),
            SelectWhereInItem(group="b", status="active"),
        ]
    )
    sqlite_session.commit()

    matched = select_where_in(
        sqlite_session,
        SelectWhereInItem,
        {"group": ["a"]},
    )

    assert len(matched) == 2
    assert {item.status for item in matched} == {"active", "inactive"}


def test_add_record_adds_and_flushes_entity(sqlite_session: Session) -> None:
    item = SelectWhereInItem(group="a", status="active")

    persisted = add_record(sqlite_session, item)

    assert persisted is item
    assert persisted.id is not None


def test_select_where_in_filters_by_multiple_fields(sqlite_session: Session) -> None:
    sqlite_session.add_all(
        [
            SelectWhereInItem(group="a", status="active"),
            SelectWhereInItem(group="a", status="inactive"),
            SelectWhereInItem(group="b", status="active"),
        ]
    )
    sqlite_session.commit()

    matched = select_where_in(
        sqlite_session,
        SelectWhereInItem,
        {"group": ["a", "b"], "status": ["active"]},
    )

    assert len(matched) == 2
    assert {(item.group, item.status) for item in matched} == {
        ("a", "active"),
        ("b", "active"),
    }


def test_select_where_in_returns_empty_for_empty_condition_values(
    sqlite_session: Session,
) -> None:
    sqlite_session.add(SelectWhereInItem(group="a", status="active"))
    sqlite_session.commit()

    matched = select_where_in(
        sqlite_session,
        SelectWhereInItem,
        {"group": []},
    )

    assert matched == []
