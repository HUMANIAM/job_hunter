from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlmodel import delete, select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from storage import Technology, create_db_and_tables, get_session


def main() -> int:
    try:
        with get_session() as session:
            result = session.exec(text("SELECT 1")).one()
            scalar_result = result[0]
            assert scalar_result == 1, (
                f"Unexpected connection test result: {result!r}"
            )
        print("DB connection OK")

        create_db_and_tables()
        print("Table creation OK")

        with get_session() as session:
            session.exec(delete(Technology))
            session.commit()

            python = Technology(name="Python", normalized_name="python")
            postgres = Technology(name="PostgreSQL", normalized_name="postgresql")
            session.add(python)
            session.add(postgres)
            session.commit()
            session.refresh(python)
            session.refresh(postgres)

            assert python.id is not None, "Python row was not assigned an id"
            assert postgres.id is not None, "PostgreSQL row was not assigned an id"
            print("Created technology: Python")
            print("Created technology: PostgreSQL")

            technologies = session.exec(
                select(Technology).order_by(Technology.normalized_name)
            ).all()
            assert len(technologies) == 2, f"Expected 2 rows, found {len(technologies)}"
            assert [row.normalized_name for row in technologies] == [
                "postgresql",
                "python",
            ], f"Unexpected rows after insert: {technologies!r}"
            print("Read count: 2")

            python_row = session.exec(
                select(Technology).where(Technology.normalized_name == "python")
            ).one()
            python_row.name = "Python 3"
            session.add(python_row)
            session.commit()
            session.refresh(python_row)
            assert python_row.name == "Python 3", "Python row was not updated"
            print("Updated technology: Python -> Python 3")

            session.delete(python_row)
            session.commit()
            remaining = session.exec(
                select(Technology).order_by(Technology.normalized_name)
            ).all()
            assert len(remaining) == 1, f"Expected 1 row after delete, found {len(remaining)}"
            assert remaining[0].normalized_name == "postgresql", (
                f"Unexpected remaining rows after delete: {remaining!r}"
            )
            print("Deleted technology: Python 3")

        print("Postgres CRUD verification PASSED")
        return 0
    except Exception as exc:
        print(f"Postgres CRUD verification FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
