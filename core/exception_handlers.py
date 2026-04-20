from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.errors import IntegrityViolationError, NotFoundError, StorageError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IntegrityViolationError)
    def _handle_integrity_violation_error(_, exc: IntegrityViolationError):
        status_code_map = {
            "unique": 409,
            "foreign_key": 400,
            "not_null": 400,
            "check": 400,
            "other": 500,
        }

        status_code = status_code_map.get(exc.kind, 500)

        message = {
            "unique": "A record with the same value already exists.",
            "foreign_key": "A referenced record does not exist.",
            "not_null": "A required field is missing.",
            "check": "The submitted data violates a database constraint.",
            "other": "The request could not be completed due to a storage constraint.",
        }.get(exc.kind, "The request could not be completed.")

        return JSONResponse(
            status_code=status_code,
            content={
                "error": "integrity_violation",
                "message": message,
                "entity": exc.entity,
                "field": exc.field,
            },
        )

    @app.exception_handler(StorageError)
    def _handle_storage_error(_, exc: StorageError):
        return JSONResponse(
            status_code=500,
            content={
                "error": "storage_error",
                "message": "An unexpected storage error occurred.",
            },
        )

    @app.exception_handler(NotFoundError)
    def _handle_not_found_error(
        _request: Request,
        exc: NotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )
