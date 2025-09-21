from app.models.time_mixin import TimeMixin
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.user import User
from app.models.file import File
from app.models.dataset import Dataset
from app.models.credential import Provider, Credential

# Export all models for easy import
__all__ = [
    "TimeMixin",
    "SoftDeleteMixin",
    "User",
    "File",
    "Dataset",
    "Provider",
    "Credential"
]

# List of all document models for Beanie initialization
DOCUMENT_MODELS = [
    User,
    File,
    Dataset,
    Provider,
    Credential
]
