"""API Key CRUD Operations"""
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate


class APIKeyCRUD:
    """CRUD operations for API keys"""

    async def create(self, owner_id: str, data: APIKeyCreate) -> tuple[APIKey, str]:
        """
        Create a new API key
        Returns: (APIKey model, actual_key_string)
        """
        # Generate the actual API key
        actual_key = APIKey.generate_key()
        key_hash = APIKey.hash_key(actual_key)
        key_prefix = APIKey.get_key_prefix(actual_key)

        # Calculate expiration
        expires_at = None
        if data.expires_in_days:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)

        # Create the API key document
        api_key = APIKey(
            owner_id=owner_id,
            name=data.name,
            chat_config_id=data.chat_config_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            is_active=True,
            expires_at=expires_at,
            permissions=data.permissions,
        )

        await api_key.insert()
        return api_key, actual_key

    async def get_by_id(self, api_key_id: str, owner_id: str) -> Optional[APIKey]:
        """Get an API key by ID"""
        return await APIKey.find_one(
            APIKey.id == ObjectId(api_key_id),
            APIKey.owner_id == owner_id
        )

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get an API key by hash (for authentication)"""
        return await APIKey.find_one(APIKey.key_hash == key_hash)

    async def list(self, owner_id: str, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> List[APIKey]:
        """List API keys for a user"""
        query = APIKey.find(APIKey.owner_id == owner_id)

        if not include_inactive:
            query = query.find(APIKey.is_active == True)

        return await query.skip(skip).limit(limit).to_list()

    async def update(self, api_key_id: str, owner_id: str, data: APIKeyUpdate) -> Optional[APIKey]:
        """Update an API key"""
        api_key = await self.get_by_id(api_key_id, owner_id)
        if not api_key:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(api_key, field, value)

        api_key.updated_at = datetime.utcnow()
        await api_key.save()
        return api_key

    async def delete(self, api_key_id: str, owner_id: str) -> bool:
        """Delete an API key"""
        api_key = await self.get_by_id(api_key_id, owner_id)
        if not api_key:
            return False

        await api_key.delete()
        return True

    async def revoke(self, api_key_id: str, owner_id: str) -> Optional[APIKey]:
        """Revoke an API key (set is_active to False)"""
        return await self.update(
            api_key_id,
            owner_id,
            APIKeyUpdate(is_active=False)
        )

    async def count(self, owner_id: str, include_inactive: bool = False) -> int:
        """Count API keys for a user"""
        query = APIKey.find(APIKey.owner_id == owner_id)

        if not include_inactive:
            query = query.find(APIKey.is_active == True)

        return await query.count()


api_key_crud = APIKeyCRUD()
