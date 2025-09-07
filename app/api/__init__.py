from app.api.webhooks import router as webhooks_router
from app.api.file import router as file_router
from app.api.folder import router as folder_router
from app.api.auth import router as auth_router

__all__ = ["webhooks_router", "file_router", "folder_router", "auth_router"]
