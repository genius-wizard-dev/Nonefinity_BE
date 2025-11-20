
import asyncio
import sys
from pathlib import Path
from app.databases.mongodb import mongodb
from app.models import DOCUMENT_MODELS
from app.services.provider_service import ProviderService
from app.utils.logging import get_logger

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


logger = get_logger(__name__)


async def main():
    """Initialize providers from YAML configuration"""
    try:
        # Connect to database
        logger.info("Connecting to MongoDB...")
        await mongodb.connect(document_models=DOCUMENT_MODELS)
        logger.info("MongoDB connection established")

        # Initialize providers
        logger.info("Loading and initializing AI providers...")
        count = await ProviderService.initialize_providers()
        logger.info(f"Successfully processed {count} providers")

    except Exception as e:
        logger.error(f"Error initializing providers: {e}")
        return 1
    finally:
        # Disconnect from database
        await mongodb.disconnect()
        logger.info("Disconnected from MongoDB")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
