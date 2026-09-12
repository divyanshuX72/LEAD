"""
Core Exceptions

Application-specific exceptions with proper HTTP mapping.
"""


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(self, entity: str, entity_id: str = ""):
        detail = f"{entity} not found" if not entity_id else f"{entity} with ID '{entity_id}' not found"
        super().__init__(detail, status_code=404, error_code="NOT_FOUND")


class DuplicateException(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409, error_code="DUPLICATE")


class ValidationException(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR")


class FileTooLargeException(AppException):
    def __init__(self, max_size_mb: int):
        super().__init__(
            f"File exceeds maximum allowed size of {max_size_mb}MB",
            status_code=413, error_code="FILE_TOO_LARGE"
        )


class UnsupportedFileTypeException(AppException):
    def __init__(self, file_type: str):
        super().__init__(
            f"File type '{file_type}' is not supported",
            status_code=415, error_code="UNSUPPORTED_FILE_TYPE"
        )


class StorageException(AppException):
    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(message, status_code=500, error_code="STORAGE_ERROR")


class DatabaseException(AppException):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR")
