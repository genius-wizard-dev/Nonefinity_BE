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
            # Create MongoDB client with sane defaults and retries
            mongo_url = settings.MONGO_URL
            self.client = AsyncIOMotorClient(
                mongo_url,
                serverSelectionTimeoutMS=8000,
                connectTimeoutMS=8000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                minPoolSize=0,
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
                logger.info(
                    f"Beanie initialized with {len(document_models)} document models")

            return True

        except ServerSelectionTimeoutError as e:
            logger.error(
                f"Failed to connect to MongoDB (timeout) at {settings.MONGO_URL}: {e}")
            raise ConnectionError("Cannot connect to MongoDB server")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")


# Global MongoDB instance
mongodb = MongoDB()
