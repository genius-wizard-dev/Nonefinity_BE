from typing import List, Optional
from app.crud.base import BaseCRUD
from app.models.credential import Credential
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

    async def get_by_owner_id(self, owner_id: str, skip: int = 0, limit: int = 100, active: Optional[bool] = None) -> List[Credential]:
        """Get credentials by owner ID"""
        filter_dict = {"owner_id": owner_id}
        if active is not None:
            filter_dict["is_active"] = active
        return await self.list(
            filter_=filter_dict,
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
        # Check for duplicate nam
        data = obj_in.model_dump()
        data["owner_id"] = owner_id

        db_obj = Credential(**data)
        await db_obj.insert()

        logger.info(f"Created credential: {db_obj.id} for owner: {owner_id}")
        return db_obj

    async def get_by_provider(self, owner_id: str, provider_id: str) -> List[Credential]:
        """Get credentials by provider ID"""
        return await self.list(
            filter_={"owner_id": owner_id, "provider_id": provider_id},
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
