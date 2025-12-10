"""
Chat export task - Export chat history to JSON/CSV files
"""
from datetime import datetime
import json
import csv
import io
import asyncio
from typing import Dict, Any

from app.tasks import celery_app
from app.services.file_service import FileService
from app.crud.task import TaskCRUD
from app.crud.user import user_crud
from app.crud.chat import chat_session_crud, chat_message_crud
from app.utils import get_logger
from app.core.exceptions import AppError

logger = get_logger(__name__)

# Flag to track if Beanie is initialized in this worker
_beanie_initialized = False


async def _init_beanie_if_needed():
    """Initialize Beanie ODM for Celery worker if not already initialized"""
    global _beanie_initialized
    if _beanie_initialized:
        return

    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from app.configs.settings import settings
    from app.models import DOCUMENT_MODELS

    client = AsyncIOMotorClient(
        settings.MONGO_URL,
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
        socketTimeoutMS=10000,
    )
    database = client[settings.MONGO_DB]
    await init_beanie(database=database, document_models=DOCUMENT_MODELS)
    _beanie_initialized = True
    logger.info("Beanie initialized for Celery worker")


async def _update_task_status(task_id: str, status: str, metadata: dict = None, error: str = None):
    """Update task status in database"""
    crud = TaskCRUD()
    update_data = {"status": status}
    if metadata:
        update_data["metadata"] = metadata
    if error:
        update_data["error"] = error

    await crud.update_status(task_id, update_data)


async def _process_export(task_id: str, config_id: str, owner_id: str, format: str) -> Dict[str, Any]:
    """Process the export operation"""
    # Initialize Beanie for Celery worker
    await _init_beanie_if_needed()

    # Update status to STARTED
    await _update_task_status(task_id, "STARTED")

    try:
        # 1. Get User for MinIO credentials
        user = await user_crud.get_by_id(owner_id)
        if not user or not user.minio_secret_key:
            raise AppError("User configuration error")

        file_service = FileService(access_key=str(user.id), secret_key=user.minio_secret_key)

        # 2. Fetch all sessions for this config
        sessions = await chat_session_crud.list(
            filter_={"chat_config_id": config_id},
            owner_id=owner_id,
            limit=10000
        )

        await _update_task_status(task_id, "PROGRESS", metadata={"total_sessions": len(sessions)})

        # 3. Process data
        export_data = []

        for session in sessions:
            messages = await chat_message_crud.list(
                filter_={"session_id": str(session.id)},
                owner_id=owner_id,
                limit=10000
            )

            session_data = {
                "session_id": str(session.id),
                "name": session.name,
                "created_at": session.created_at.isoformat(),
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "tools": msg.tools
                    }
                    for msg in messages
                ]
            }
            export_data.append(session_data)

        # 4. Generate File Content
        file_content = b""
        extension = ""
        mime_type = ""

        if format.lower() == "json":
            file_content = json.dumps(export_data, indent=2, ensure_ascii=False).encode('utf-8')
            extension = ".json"
            mime_type = "application/json"
        elif format.lower() == "csv":
            # Flatten for CSV: session_id, session_name, message_role, message_content, message_time
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["session_id", "session_name", "role", "content", "created_at"])

            for session in export_data:
                for msg in session["messages"]:
                    writer.writerow([
                        session["session_id"],
                        session["name"],
                        msg["role"],
                        msg["content"],
                        msg["created_at"]
                    ])
            file_content = output.getvalue().encode('utf-8')
            extension = ".csv"
            mime_type = "text/csv"

        # 5. Upload to MinIO
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_export_{config_id}_{timestamp}{extension}"
        object_name = f"exports/{filename}"

        # Determine bucket (owner_id)
        bucket_name = str(user.id)

        success = await file_service._minio_client.async_upload_bytes(
            bucket_name=bucket_name,
            object_name=object_name,
            data=file_content,
            content_type=mime_type
        )

        if not success:
            raise AppError("Failed to upload export file")

        # 6. Save File Metadata
        file_meta = await file_service.save_file_metadata(
            user_id=owner_id,
            object_name=object_name,
            file_name=filename,
            file_type=mime_type,
            file_size=len(file_content),
            source_file="export"
        )

        # 7. Complete Task
        result_metadata = {
            "file_id": str(file_meta.id),
            "file_name": file_meta.file_name,
            "session_count": len(sessions)
        }

        await _update_task_status(task_id, "SUCCESS", metadata=result_metadata)

        return result_metadata

    except Exception as e:
        logger.error(f"Process export failed: {str(e)}")
        await _update_task_status(task_id, "FAILURE", error=str(e))
        raise e


@celery_app.task(name="tasks.chat.export_history")
def export_chat_history(task_id: str, config_id: str, owner_id: str, format: str = "csv") -> Dict[str, Any]:
    """
    Export all chat history for a config to a file (JSON or CSV)

    Args:
        task_id: Task identifier for tracking
        config_id: Chat config ID to export
        owner_id: Owner user ID
        format: Export format ('json' or 'csv')

    Returns:
        Dict with file_id, file_name, session_count
    """
    logger.info(f"Starting export task: {task_id} for config: {config_id}")

    # Get or create event loop - reuse existing to keep Motor client alive
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _process_export(task_id, config_id, owner_id, format)
        )
        return result
    except Exception as e:
        logger.error(f"Export task failed: {str(e)}")
        # Update task status to ERROR (need to init Beanie first)
        try:
            loop.run_until_complete(_init_beanie_if_needed())
            loop.run_until_complete(_update_task_status(task_id, "ERROR", error=str(e)))
        except Exception as update_err:
            logger.error(f"Failed to update task status: {update_err}")
        raise e
    # NOTE: Do NOT close the loop - Motor client needs it to stay alive for connection reuse

