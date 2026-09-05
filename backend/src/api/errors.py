"""Domain error to HTTP status. The only place that knows about both."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    DomainError,
    EmptyUpload,
    FieldRequired,
    FieldTooLong,
    FileNotFound,
    StoredPayloadMissing,
    UploadTooLarge,
)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    FileNotFound: status.HTTP_404_NOT_FOUND,
    StoredPayloadMissing: status.HTTP_404_NOT_FOUND,
    EmptyUpload: status.HTTP_400_BAD_REQUEST,
    FieldRequired: status.HTTP_400_BAD_REQUEST,
    FieldTooLong: status.HTTP_400_BAD_REQUEST,
    UploadTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
}

DETAIL_BY_ERROR: dict[type[DomainError], str] = {
    FileNotFound: "File not found",
    StoredPayloadMissing: "Stored file not found",
    EmptyUpload: "File is empty",
    FieldRequired: "Value must not be empty",
    FieldTooLong: "Value is too long",
    UploadTooLarge: "File is too large",
}


async def domain_error_handler(request: Request, error: Exception) -> JSONResponse:
    # Starlette hands every handler a bare Exception; only DomainError reaches
    # this one, and anything else is a programming mistake worth surfacing.
    if not isinstance(error, DomainError):
        raise error
    code = STATUS_BY_ERROR.get(type(error), status.HTTP_400_BAD_REQUEST)
    detail = DETAIL_BY_ERROR.get(type(error), str(error))
    return JSONResponse(status_code=code, content={"detail": detail})
