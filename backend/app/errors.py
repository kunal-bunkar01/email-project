class AppError(Exception):
    """User-facing application error. Technical detail stays in the logs."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
