from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")

class Pagination(BaseModel):
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    pages: int = Field(..., ge=1)
    next: Optional[str] = None
    previous: Optional[str] = None
    
class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    meta: Optional[Pagination] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None
    
class ApiError(BaseModel): 
    success: bool = False,
    message: str
    errros: Optional[List[ErrorDetail]] = None