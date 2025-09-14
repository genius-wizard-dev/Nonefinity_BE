from fastapi import APIRouter, HTTPException
from app.databases import get_instance_manager
from app.utils import get_logger
from app.schemas.response import ApiResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_duckdb_stats():
    """
    Lấy thống kê về DuckDB instances hiện tại

    Returns:
        Dict chứa thông tin về số lượng instances, TTL, cleanup interval, etc.
    """
    try:
        manager = get_instance_manager()
        stats = manager.get_stats()

        logger.info(f"DuckDB stats retrieved: {stats}")

        return ApiResponse(
            success=True,
            message="Lấy thống kê DuckDB instances thành công",
            data=stats
        )

    except Exception as e:
        logger.error(f"Lỗi khi lấy thống kê DuckDB: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi server khi lấy thống kê: {str(e)}"
        )


@router.post("/cleanup")
async def force_cleanup():
    """
    Buộc cleanup tất cả instances hết hạn

    Returns:
        Thông báo cleanup thành công
    """
    try:
        manager = get_instance_manager()
        manager.cleanup_expired_instances()

        logger.info("Manual cleanup DuckDB instances completed")

        return ApiResponse(
            success=True,
            message="Cleanup DuckDB instances thành công"
        )

    except Exception as e:
        logger.error(f"Lỗi khi cleanup DuckDB instances: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi server khi cleanup: {str(e)}"
        )
