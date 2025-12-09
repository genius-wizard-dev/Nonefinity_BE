from typing import Any, Dict, List, Optional
from starlette import status

class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "bad_request",
        field: Optional[str] = None,
        errors: Optional[List[dict]] = None,  # [{'code':..., 'message':..., 'field':...}]
        details: Optional[Dict[str, Any]] = None,  # Additional details for the error
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.field = field
        self.errors = errors
        self.details = details
