from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document
from pymongo.errors import ServerSelectionTimeoutError

from app.configs.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

class MongoDB:
    """Simplified MongoDB connection manager using Beanie ODM"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        
    async def connect(self, document_models: List[Document] = None):
        """Connect to MongoDB and initialize Beanie"""
        try:
            # Create MongoDB client with shorter timeouts
            self.client = AsyncIOMotorClient(
                settings.MONGO_URL,
                serverSelectionTimeoutMS=3000,  # 3 second timeout
                connectTimeoutMS=5000,          # 5 second connection timeout
                socketTimeoutMS=5000            # 5 second socket timeout
            )
            
            # Test connection
            await self.client.admin.command('ping')
            # logger.info(f"Connected to MongoDB at {settings.MONGO_HOST}:{settings.MONGO_PORT}")
            
            # Get database
            self.database = self.client[settings.MONGO_DB]
            
            # Initialize Beanie with document models
            if document_models:
                await init_beanie(
                    database=self.database,
                    document_models=document_models
                )
                logger.info(f"Beanie initialized with {len(document_models)} document models")
            
            return True
            
        except ServerSelectionTimeoutError:
            logger.error("Failed to connect to MongoDB: Server selection timeout")
            raise ConnectionError("Cannot connect to MongoDB server")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def check_connection(self) -> bool:
        """Check if MongoDB connection is alive"""
        try:
            if self.client:
                await self.client.admin.command('ping')
                return True
            return False
        except Exception:
            return False
    
    async def get_database_info(self) -> dict:
        """Get basic database information"""
        try:
            if self.database is None:
                return {}
                
            collections = await self.database.list_collection_names()
            
            return {
                "database_name": self.database.name,
                "collections": collections,
                "collections_count": len(collections)
            }
        except Exception as e:
            logger.error(f"Error getting database info: {str(e)}")
            return {}

# Global MongoDB instance
mongodb = MongoDB()

async def get_mongodb() -> MongoDB:
    """Get MongoDB instance"""
    return mongodb
