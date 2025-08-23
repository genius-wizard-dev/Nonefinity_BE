from fastapi import APIRouter, HTTPException
from app.databases.mongodb import mongodb
from app.services.mongodb_service import mongodb_service
from app.models import DOCUMENT_MODELS
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["MongoDB"])

@router.get("/health", summary="Check database health")
async def check_database_health():
    """Check if database connection is healthy"""
    try:
        is_connected = await mongodb.check_connection()
        
        if not is_connected:
            raise HTTPException(status_code=503, detail="Database connection is down")
        
        return {
            "status": "healthy",
            "connected": True,
            "message": "Database connection is working properly"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")

@router.get("/info", summary="Get database information")
async def get_database_info():
    """Get comprehensive database information"""
    try:
        db_info = await mongodb.get_database_info()
        return {
            "status": "success",
            "data": db_info
        }
    except Exception as e:
        logger.error(f"Failed to get database info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get database info: {str(e)}")

@router.get("/statistics", summary="Get detailed database statistics")
async def get_database_statistics():
    """Get detailed database and collection statistics"""
    try:
        stats = await mongodb_service.get_database_statistics()
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get database statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get database statistics: {str(e)}")

@router.get("/schema/check", summary="Check schema compatibility")
async def check_schema_compatibility():
    """Check if database schema needs setup"""
    try:
        compatibility_report = await mongodb_service.check_schema_compatibility(DOCUMENT_MODELS)
        return {"status": "success", "data": compatibility_report}
    except Exception as e:
        logger.error(f"Schema check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/models", summary="Get information about Beanie models")
async def get_model_information():
    """Get basic information about registered models"""
    try:
        models_info = []
        
        for model in DOCUMENT_MODELS:
            models_info.append({
                "name": model.__name__,
                "collection": model.get_collection_name()
            })
        
        return {
            "status": "success",
            "data": {
                "total_models": len(DOCUMENT_MODELS),
                "models": models_info
            }
        }
    except Exception as e:
        logger.error(f"Failed to get model information: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections", summary="List all collections")
async def list_collections():
    """List all collections in the database"""
    try:
        if mongodb.database is None:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        collections = await mongodb.database.list_collection_names()
        
        return {
            "status": "success",
            "data": {
                "total_collections": len(collections),
                "collections": collections
            }
        }
    except Exception as e:
        logger.error(f"Failed to list collections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections/{collection_name}/indexes", summary="Get indexes for a collection")
async def get_collection_indexes(collection_name: str):
    """Get all indexes for a specific collection"""
    try:
        if mongodb.database is None:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        collection = mongodb.database[collection_name]
        indexes = await collection.list_indexes().to_list(None)
        
        return {
            "status": "success",
            "data": {
                "collection": collection_name,
                "total_indexes": len(indexes),
                "indexes": indexes
            }
        }
    except Exception as e:
        logger.error(f"Failed to get indexes for collection {collection_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
