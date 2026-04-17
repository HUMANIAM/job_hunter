from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlmodel import Session


CLIENTS_TESTS_DIR = Path(__file__).parent.resolve()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        item_path = Path(str(item.path)).resolve()
        if CLIENTS_TESTS_DIR in item_path.parents:
            item.add_marker(pytest.mark.clients_suite)


@pytest.fixture
def mock_session() -> Mock:
    session = Mock(spec=Session)

    def _refresh(record) -> None:
        record.id = 1

    session.refresh.side_effect = _refresh
    return session


@pytest.fixture
def set_exec_first():
    def _set_exec_first(session: Mock, value: object) -> Mock:
        exec_result = Mock()
        exec_result.first.return_value = value
        session.exec.return_value = exec_result
        return exec_result

    return _set_exec_first
