from math import ceil
from typing import Any, Dict, List, Optional, Sequence

from fastapi import Request
from starlette.responses import JSONResponse, Response
from starlette import status

from app.schemas.response import ApiResponse, Pagination

def ok(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK,
    headers: Optional[Dict[str, str]] = None,
):
    body = ApiResponse[Any](success=True, message=message, data=data).model_dump(mode="json", exclude_none=True)
    return JSONResponse(content=body, status_code=status_code, headers=headers)

def created(
    data: Any = None,
    message: str = "Created",
    headers: Optional[Dict[str, str]] = None,
):
    body = ApiResponse[Any](success=True, message=message, data=data).model_dump(mode="json", exclude_none=True)
    return JSONResponse(content=body, status_code=status.HTTP_201_CREATED, headers=headers)



def no_content() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)

def _page_url(request: Request, page: int, page_size: int) -> str:
    qp = dict(request.query_params)
    qp["page"] = str(page)
    qp["page_size"] = str(page_size)
    return str(request.url.replace_query_params(**qp))

def paginated(
    *,
    request: Request,
    items: Sequence[Any],
    total: int,
    page: int,
    page_size: int,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK,
):
    pages = max(1, ceil(total / page_size)) if page_size > 0 else 1

    next_url = _page_url(request, page + 1, page_size) if page < pages else None
    prev_url = _page_url(request, page - 1, page_size) if page > 1 else None

    meta = Pagination(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        next=next_url,
        previous=prev_url,
    )

    body = ApiResponse[List[Any]](
        success=True,
        message=message,
        data=list(items),
        meta=meta,
    ).model_dump(mode="json", exclude_none=True)

    return JSONResponse(content=body, status_code=status_code)
