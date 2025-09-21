from typing import List, Optional
from app.crud.base import BaseCRUD
from app.models.credential import Credential
from app.models.provider import Provider
from app.schemas.credential import CredentialCreate, CredentialUpdate
from app.utils import get_logger

logger = get_logger(__name__)


class CredentialCRUD(BaseCRUD[Credential, CredentialCreate, CredentialUpdate]):
    def __init__(self):
        super().__init__(Credential)

    async def get_by_owner_and_name(self, owner_id: str, name: str) -> Optional[Credential]:
        """Get credential by owner ID and name"""
        return await self.get_one(
            filter_={"owner_id": owner_id, "name": name},
            include_deleted=False
        )

    async def get_by_owner_id(self, owner_id: str, skip: int = 0, limit: int = 100) -> List[Credential]:
        """Get credentials by owner ID"""
        return await self.list(
            filter_={"owner_id": owner_id},
            skip=skip,
            limit=limit,
            include_deleted=False
        )

    async def get_by_owner_and_id(self, owner_id: str, credential_id: str) -> Optional[Credential]:
        """Get credential by owner and ID"""
        credential = await self.get_by_id(credential_id, include_deleted=False)
        if credential and credential.owner_id == owner_id:
            return credential
        return None

    async def create_with_owner(self, owner_id: str, obj_in: CredentialCreate) -> Credential:
        """Create credential with owner_id"""
        # Verify provider exists and is active
        provider = await Provider.find_one(
            Provider.provider == obj_in.provider,
            Provider.is_active
        )
        if not provider:
            raise ValueError(f"Provider '{obj_in.provider}' not found or inactive")

        # Check for duplicate name
        existing = await self.get_by_owner_and_name(owner_id, obj_in.name)
        if existing:
            raise ValueError(f"Credential with name '{obj_in.name}' already exists")

        # Create credential with owner_id
        data = obj_in.model_dump()
        data["owner_id"] = owner_id

        db_obj = Credential(**data)
        await db_obj.insert()

        logger.info(f"Created credential: {db_obj.id} for owner: {owner_id}")
        return db_obj

    async def get_by_provider(self, owner_id: str, provider: str) -> List[Credential]:
        """Get credentials by provider"""
        return await self.list(
            filter_={"owner_id": owner_id, "provider": provider},
            include_deleted=False
        )

    async def count_by_owner(self, owner_id: str) -> int:
        """Count credentials by owner"""
        credentials = await self.list(
            filter_={"owner_id": owner_id},
            include_deleted=False
        )
        return len(credentials)


# Create instance
credential_crud = CredentialCRUD()
