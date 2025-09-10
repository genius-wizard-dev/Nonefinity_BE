from __future__ import annotations

from typing import Literal
from starlette import status
from app.core.exceptions import AppError

# Root constants - chỉ có 3 root folder cố định
RAW_ROOT = "raw"
PROCESS_ROOT = "process"
KNOWLEDGE_ROOT = "knowledge"

APIType = Literal["upload", "process", "knowledge"]


def get_root_for_api(api_type: APIType) -> str:
    """Trả về root folder tương ứng với loại API"""
    mapping = {
        "upload": RAW_ROOT,
        "process": PROCESS_ROOT,
        "knowledge": KNOWLEDGE_ROOT,
    }
    if api_type not in mapping:  # type: ignore[truthy-bool]
        raise AppError(
            message="Loại API không hợp lệ",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_api_type",
            field="api_type",
        )
    return mapping[api_type]


def validate_api_access(root_type: str, api_type: APIType) -> None:
    """
    Kiểm tra xem API có quyền truy cập vào root_type không.
    Raise AppError nếu không có quyền.
    """
    expected_root = get_root_for_api(api_type)
    if root_type != expected_root:
        raise AppError(
            message=f"Không được truy cập sang vùng khác: yêu cầu thuộc {expected_root}",
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden_path",
            field="root_type",
        )


def get_object_path(root_type: str, filename: str) -> str:
    """
    Tạo object path cho MinIO từ root_type và filename.
    Ví dụ: get_object_path("raw", "test.pdf") -> "raw/test.pdf"
    """
    if not root_type or not filename:
        raise AppError(
            message="Root type và filename không được để trống",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_path_params",
        )
    return f"{root_type}/{filename}"


__all__ = [
    "RAW_ROOT",
    "PROCESS_ROOT",
    "KNOWLEDGE_ROOT",
    "get_root_for_api",
    "validate_api_access",
    "get_object_path",
]


