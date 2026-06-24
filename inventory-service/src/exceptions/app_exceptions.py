class AppError(Exception):
    """Base class for all application-specific exceptions."""
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppError):
    """Raised when an inventory record does not exist for a product."""
    def __init__(self, message="Resource not found"):
        super().__init__(message, 404)


class BadRequestError(AppError):
    """Raised for general invalid requests."""
    def __init__(self, message="Bad request"):
        super().__init__(message, 400)


class ConflictError(AppError):
    """Raised during inventory race conditions, e.g., insufficient stock available to reserve."""
    def __init__(self, message="Resource conflict or insufficient stock"):
        super().__init__(message, 409)


class DatabaseError(AppError):
    """Raised when DynamoDB fails unexpectedly (network issues, table missing)."""
    def __init__(self, message="Database operation failed"):
        super().__init__(message, 500)