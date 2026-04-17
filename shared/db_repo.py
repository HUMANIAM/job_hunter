from typing import Callable, TypeVar

from sqlalchemy.exc import IntegrityError

from shared.map_postgres_integrity_error import map_postgres_integrity_error
from core.errors import StorageError


T = TypeVar("T")


def commit_if_requested_or_raise(
    session,
    *,
    commit: bool,
    operation: str,
    entity: str,
    fn: Callable[[], T],
) -> T:
    """
    Run a persistence operation with standardized Postgres error mapping.

    Contract:
      - Calls `fn()` to perform persistence work (flush/SQL/etc).
      - If commit=True:
          - commits on success
          - rolls back before raising on failure
      - If commit=False:
          - does not commit
          - does not rollback on failure

    Raises:
      - IntegrityViolationError: mapped from Postgres IntegrityError
      - StorageError: unexpected persistence failures
    """
    success = False
    try:
        result = fn()
        if commit:
            session.commit()
        success = True
        return result

    except IntegrityError as e:
        raise map_postgres_integrity_error(
            e,
            operation=operation,
            entity=entity,
        ) from e

    except Exception as e:
        raise StorageError(
            operation=operation,
            detail=str(e),
        ) from e

    finally:
        if commit and not success:
            session.rollback()
