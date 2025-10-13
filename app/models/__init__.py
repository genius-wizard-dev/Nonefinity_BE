from app.models.time_mixin import TimeMixin
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.user import User
from app.models.file import File
from app.models.dataset import Dataset
from app.models.provider import Provider, ProviderTaskConfig
from app.models.credential import Credential
from app.models.model import Model
from app.models.task import Task
from app.models.knowledge_store import KnowledgeStore

# Export all models for easy import
__all__ = [
    "TimeMixin",
    "SoftDeleteMixin",
    "User",
    "File",
    "Dataset",
    "Provider",
    "ProviderTaskConfig",
    "Credential",
    "Model",
    "KnowledgeStore"
]

# List of all document models for Beanie initialization
DOCUMENT_MODELS = [
    User,
    File,
    Dataset,
    Provider,
    ProviderTaskConfig,
    Credential,
    Model,
    Task,
    KnowledgeStore
]
