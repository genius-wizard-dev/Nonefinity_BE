"""
Celery tasks module for embedding operations
"""

from celery import Celery
from celery.signals import task_success, task_failure, task_retry, task_revoked
from app.configs.settings import settings
from app.tasks.embed import run_embedding, run_text_embedding, search_similar
from app.utils import get_logger
import asyncio

logger = get_logger(__name__)

# Create Celery app instance
celery_app = Celery(
    "embedding_tasks",
    broker=settings.get_broker_url,
    backend=settings.get_result_backend,
)

# Configure Celery app
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    result_expires=3600,  # Results expire after 1 hour
    task_ignore_result=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,  # Suppress deprecation warning
    task_routes={
        'tasks.embedding.run_embedding': {'queue': 'embeddings'},
        'tasks.embedding.run_text_embedding': {'queue': 'embeddings'},
        'tasks.embedding.search_similar': {'queue': 'embeddings'},
    },
)

# Register tasks with Celery app
celery_app.task(name='tasks.embedding.run_embedding')(run_embedding)
celery_app.task(name='tasks.embedding.run_text_embedding')(run_text_embedding)
celery_app.task(name='tasks.embedding.search_similar')(search_similar)


# Celery signals for updating task status in MongoDB
@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Update task status to SUCCESS in MongoDB when task completes successfully"""
    task_id = kwargs.get('task_id')
    if not task_id:
        return

    try:
        from app.crud.task import TaskCRUD
        import asyncio

        async def update_task():
            try:
                task_crud = TaskCRUD()
                task_doc = await task_crud.get_by_task_id(task_id)
                if task_doc:
                    update_data = {
                        "status": "SUCCESS",
                        "metadata": task_doc.metadata or {}
                    }
                    if isinstance(result, dict):
                        update_data["metadata"]["result"] = result
                    await task_crud.update(task_doc, update_data)
                    logger.info(f"✅ Task {task_id} marked as SUCCESS in MongoDB")
                else:
                    logger.warning(f"⚠️ Task {task_id} not found in MongoDB for success update")
            except Exception as inner_e:
                logger.error(f"❌ Error in update_task coroutine for {task_id}: {inner_e}", exc_info=True)

        # Try to get existing event loop, if not create a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(update_task())
    except Exception as e:
        logger.error(f"❌ Failed to update task status on success for {task_id}: {e}", exc_info=True)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """Update task status to FAILURE in MongoDB when task fails"""
    if not task_id:
        return

    try:
        from app.crud.task import TaskCRUD
        import asyncio

        async def update_task():
            try:
                task_crud = TaskCRUD()
                task_doc = await task_crud.get_by_task_id(task_id)
                if task_doc:
                    await task_crud.update(task_doc, {
                        "status": "FAILURE",
                        "error": str(exception) if exception else "Unknown error"
                    })
                    logger.info(f"✅ Task {task_id} marked as FAILURE in MongoDB")
                else:
                    logger.warning(f"⚠️ Task {task_id} not found in MongoDB for failure update")
            except Exception as inner_e:
                logger.error(f"❌ Error in update_task coroutine for {task_id}: {inner_e}", exc_info=True)

        # Try to get existing event loop, if not create a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(update_task())
    except Exception as e:
        logger.error(f"❌ Failed to update task status on failure for {task_id}: {e}", exc_info=True)


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, **kwargs):
    """Update task status to RETRY in MongoDB when task is retried"""
    if not task_id:
        return

    try:
        from app.crud.task import TaskCRUD
        import asyncio

        async def update_task():
            try:
                task_crud = TaskCRUD()
                task_doc = await task_crud.get_by_task_id(task_id)
                if task_doc:
                    await task_crud.update(task_doc, {
                        "status": "RETRY",
                        "error": str(reason) if reason else "Retrying task"
                    })
                    logger.info(f"✅ Task {task_id} marked as RETRY in MongoDB")
                else:
                    logger.warning(f"⚠️ Task {task_id} not found in MongoDB for retry update")
            except Exception as inner_e:
                logger.error(f"❌ Error in update_task coroutine for {task_id}: {inner_e}", exc_info=True)

        # Try to get existing event loop, if not create a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(update_task())
    except Exception as e:
        logger.error(f"❌ Failed to update task status on retry for {task_id}: {e}", exc_info=True)


@task_revoked.connect
def task_revoked_handler(sender=None, request=None, **kwargs):
    """Update task status to REVOKED in MongoDB when task is revoked"""
    task_id = request.id if request else None
    if not task_id:
        return

    try:
        from app.crud.task import TaskCRUD
        import asyncio

        async def update_task():
            try:
                task_crud = TaskCRUD()
                task_doc = await task_crud.get_by_task_id(task_id)
                if task_doc:
                    await task_crud.update(task_doc, {
                        "status": "REVOKED",
                        "error": "Task was cancelled/revoked"
                    })
                    logger.info(f"✅ Task {task_id} marked as REVOKED in MongoDB")
                else:
                    logger.warning(f"⚠️ Task {task_id} not found in MongoDB for revoke update")
            except Exception as inner_e:
                logger.error(f"❌ Error in update_task coroutine for {task_id}: {inner_e}", exc_info=True)

        # Try to get existing event loop, if not create a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(update_task())
    except Exception as e:
        logger.error(f"❌ Failed to update task status on revoke for {task_id}: {e}", exc_info=True)


__all__ = ["celery_app"]
