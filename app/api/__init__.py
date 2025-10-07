from app.api.webhooks import router as webhooks_router
from app.api.file import router as file_router
from app.api.auth import router as auth_router
from app.api.duckdb import router as duckdb_router
from app.api.dataset import router as dataset_router
from app.api.credential import router as credential_router
from app.api.provider import router as provider_router
from app.api.embedding import router as embedding_router
from app.api.model import router as model_router
from app.api.tasks import router as tasks_router

__all__ = ["webhooks_router", "file_router", "auth_router", "duckdb_router", "dataset_router", "credential_router", "provider_router", "embedding_router", "model_router", "tasks_router"]
