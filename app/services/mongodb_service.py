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

# Global service instance
mongodb_service = MongoDBService()
