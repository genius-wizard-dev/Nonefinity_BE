from typing import Dict, List, Any
from pymongo import IndexModel
from pymongo.errors import OperationFailure
from beanie import Document

from app.databases.mongodb import mongodb
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MongoDBService:
    """Simplified service for database operations"""
    
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        """Initialize the service with database connection"""
        self.db = mongodb.database
    
    async def check_schema_compatibility(self, document_models: List[Document]) -> Dict[str, Any]:
        """Simplified schema compatibility check"""
        if self.db is None:
            await self.initialize()
            
        try:
            existing_collections = await self.db.list_collection_names()
            missing_collections = []
            
            for model in document_models:
                collection_name = model.get_collection_name()
                if collection_name not in existing_collections:
                    missing_collections.append(collection_name)
            
            return {
                "status": "compatible" if not missing_collections else "issues_found",
                "missing_collections": missing_collections,
                "total_models": len(document_models),
                "needs_setup": len(missing_collections) > 0
            }
            
        except Exception as e:
            logger.error(f"Error checking schema compatibility: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "needs_setup": True
            }
    
    async def _index_exists(self, collection, index_spec) -> bool:
        """Simple check if an index exists"""
        try:
            existing_indexes = await collection.list_indexes().to_list(None)
            
            # Convert spec to comparable format
            if isinstance(index_spec, list):
                target_key = dict(index_spec)
            elif isinstance(index_spec, dict):
                target_key = index_spec
            else:
                target_key = {str(index_spec): 1}
            
            # Check if any existing index matches
            for idx in existing_indexes:
                if idx.get('key', {}) == target_key:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking index existence: {e}")
            return False
    
    async def create_missing_collections_and_indexes(self, document_models: List[Document]) -> Dict[str, Any]:
        """Simplified collection and index creation"""
        if self.db is None:
            await self.initialize()
        
        result = {
            "status": "success",
            "created_collections": [],
            "created_indexes": [],
            "errors": []
        }
        
        try:
            existing_collections = await self.db.list_collection_names()
            
            for model in document_models:
                collection_name = model.get_collection_name()
                
                # Create collection if missing
                if collection_name not in existing_collections:
                    await self.db.create_collection(collection_name)
                    result["created_collections"].append(collection_name)
                    logger.info(f"Created collection: {collection_name}")
                
                # Create basic indexes if defined
                if hasattr(model, 'Settings') and hasattr(model.Settings, 'indexes'):
                    indexes = model.Settings.indexes or []
                    collection = self.db[collection_name]
                    
                    for index in indexes:
                        try:
                            # Extract key specification
                            if isinstance(index, IndexModel):
                                key_spec = index.document
                            else:
                                key_spec = index
                            
                            # Skip if exists
                            if await self._index_exists(collection, key_spec):
                                continue
                            
                            # Create index
                            index_name = await collection.create_index(key_spec)
                            result["created_indexes"].append({
                                "collection": collection_name,
                                "index": index_name
                            })
                            logger.info(f"Created index for {collection_name}")
                            
                        except OperationFailure as e:
                            if "already exists" not in str(e):
                                error_msg = f"Index creation failed for {collection_name}: {str(e)}"
                                result["errors"].append(error_msg)
                                logger.warning(error_msg)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in database setup: {str(e)}")
            result["status"] = "error"
            result["error"] = str(e)
            return result
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """Get basic database statistics"""
        if self.db is None:
            await self.initialize()
        
        try:
            db_stats = await self.db.command("dbstats")
            collections = await self.db.list_collection_names()
            
            return {
                "database_name": self.db.name,
                "collections_count": len(collections),
                "total_size": db_stats.get("dataSize", 0),
                "collections": collections
            }
            
        except Exception as e:
            logger.error(f"Error getting database statistics: {str(e)}")
            return {"error": str(e)}


# Global service instance
mongodb_service = MongoDBService()
