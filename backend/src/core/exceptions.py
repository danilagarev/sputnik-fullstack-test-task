"""Domain errors.

The service layer raises these instead of ``HTTPException``: that is what lets
the same code run inside a Celery worker, where there is no request to answer.
Translating them into status codes is the API layer's job.
"""


class DomainError(Exception):
    """Base class for everything the domain can refuse to do."""


class FileNotFound(DomainError):
    def __init__(self, file_id: str) -> None:
        super().__init__(f"File {file_id} not found")
        self.file_id = file_id


class StoredPayloadMissing(DomainError):
    """The row exists but the bytes it points at do not."""


class EmptyUpload(DomainError):
    pass


class UploadTooLarge(DomainError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Upload exceeds the {limit} byte limit")
        self.limit = limit


class FieldRequired(DomainError):
    def __init__(self, field: str) -> None:
        super().__init__(f"{field} must not be empty")
        self.field = field


class FieldTooLong(DomainError):
    def __init__(self, field: str, limit: int) -> None:
        super().__init__(f"{field} exceeds {limit} characters")
        self.field = field
        self.limit = limit
