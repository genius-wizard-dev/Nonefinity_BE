import base64
from typing import Optional, Any, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import InvalidToken
from app.services import redis_service
from app.schemas.credential import (
    CredentialCreate, CredentialUpdate, CredentialDetail,
    CredentialList, ModelCredentialResponse
)
from app.schemas.provider import ProviderResponse, ProviderList
from app.services.provider_service import ProviderService
from app.configs.settings import settings
from app.core.exceptions import AppError
from app.schemas.model import ModelType
from app.utils import get_logger
from app.utils.request import get
from app.crud import model_crud, credential_crud
logger = get_logger(__name__)


class CredentialService:
    def __init__(self):
        self.crud = credential_crud
        self.model_crud = model_crud
        self._cipher_suite = None
        self._initialize_encryption()


    def _initialize_encryption(self):
        """Initialize encryption with key derivation from environment variables"""
        try:
            # Get encryption parameters from settings (validated at startup)
            secret_key = settings.CREDENTIAL_SECRET_KEY
            salt = settings.CREDENTIAL_ENCRYPTION_SALT.encode('utf-8')
            iterations = settings.CREDENTIAL_KDF_ITERATIONS


            # Derive encryption key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits for Fernet
                salt=salt,
                iterations=iterations,
            )

            derived_key = kdf.derive(secret_key.encode('utf-8'))
            fernet_key = base64.urlsafe_b64encode(derived_key)
            self._cipher_suite = Fernet(fernet_key)

            logger.info("✅ Credential encryption system initialized successfully")

        except AttributeError as e:
            logger.error(f"❌ Missing credential environment variable: {e}")
            raise AppError(
                message="Missing required credential encryption environment variables. Check your .env file.",
                status_code=500
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize credential encryption: {e}")
            raise AppError(
                message=f"Failed to initialize credential encryption system: {str(e)}",
                status_code=500
            )

    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage"""
        try:
            if not api_key or not api_key.strip():
                raise ValueError("API key cannot be empty")

            # Fernet automatically handles encoding and creates a token
            encrypted_token = self._cipher_suite.encrypt(api_key.encode('utf-8'))

            # Return the encrypted token as base64 string for storage
            return base64.urlsafe_b64encode(encrypted_token).decode('utf-8')

        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            raise AppError(
                message="Failed to encrypt API key for storage",
                status_code=500
            )

    def _decrypt_api_key(self, encrypted_api_key: str) -> str:
        """Decrypt API key for use"""
        try:
            if not encrypted_api_key:
                raise ValueError("Encrypted API key cannot be empty")

            # Decode from base64 and decrypt using Fernet
            encrypted_token = base64.urlsafe_b64decode(encrypted_api_key.encode('utf-8'))
            decrypted_data = self._cipher_suite.decrypt(encrypted_token)

            return decrypted_data.decode('utf-8')

        except InvalidToken:
            logger.error("Invalid token encountered during API key decryption")
            raise AppError(
                message="Failed to decrypt API key - invalid token",
                status_code=500
            )
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise AppError(
                message="Failed to decrypt API key",
                status_code=500
            )

    async def _verify_and_get_model_credential(self, base_url: str, api_key: str, provider: str) -> tuple[bool, str]:
        """Get model credential, return (success, error_message)"""
        try:
            models = []
            models_url = base_url + "/models"
            if provider == "google_genai":
              result = await get(models_url + "?key=" + api_key)
              if isinstance(result, dict) and "error" in result:
                  error = result["error"]
                  error_message = error.get('message', str(error))
                  logger.error(f"API error when validating models: {error_message}")
                  return False, error_message
              elif isinstance(result, dict) and isinstance(result.get("models"), list):
                  result = result.get("models")
                  models = [
                    ModelCredentialResponse.model_validate(
                        {
                        "id": model.get("name"),
                        "object": "model",
                        "created": 0,
                        "owned_by": provider
                        })
                    for model in result
                  ]
              else:
                  error_message = f"Unexpected response format: {result}"
                  logger.error(f"Unexpected response format when validating API key/models: {result}")
                  return False, error_message

              if models:
                  data = await redis_service.jget(f"provider:{provider}")
                  if data:
                      return True, ""
                  else:
                      await redis_service.jset(
                          f"provider:{provider}",
                          [model.model_dump() for model in models],
                          ex=86400
                      )
                      return True, ""
              else:
                  return False, "No models found"
            else:
                # For other providers, skip validation (they may have different validation logic)
                return True, ""

        except Exception as e:
            error_message = f"Failed to get model credential: {e}"
            logger.error(error_message)
            return False, error_message

    async def create_credential(self, owner_id: str, credential_data: CredentialCreate):
        """Create a new credential with API key validation, return bool indicating success"""
        # Get provider information first for validation
        existing_credential = await self.crud.get_by_owner_and_name(owner_id, credential_data.name)
        if existing_credential:
            raise ValueError(f"Credential with name '{credential_data.name}' already exists")

        provider = await ProviderService.get_provider_by_id(credential_data.provider_id)
        if not provider:
            raise ValueError(f"Provider with ID '{credential_data.provider_id}' not found or inactive")

        if not credential_data.base_url:
            credential_data.base_url = provider.base_url


        verify_token, error_message = await self._verify_and_get_model_credential(
            provider=provider.provider,
            api_key=credential_data.api_key,
            base_url=credential_data.base_url
        )

        if not verify_token:
            error_msg = 'Invalid API key'
            if error_message:
                error_msg = f"{error_msg}. Provider error: {error_message}"
            raise ValueError(f"API key validation failed: {error_msg}")


        encrypted_data = credential_data.model_copy()
        encrypted_data.api_key = self._encrypt_api_key(credential_data.api_key)

        try:
            db_credential = await self.crud.create_with_owner(owner_id, encrypted_data)
            if db_credential:
                return db_credential
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to create credential: {e}")
            return None

    async def get_credentials(
        self,
        owner_id: str,
        skip: int = 0,
        limit: int = 100,
        active: Optional[bool] = None,
        task_type: Optional[ModelType] = None
    ) -> CredentialList:
        """Get owner credentials"""
        credentials = await self.crud.get_by_owner_id(owner_id, skip, limit, active)
        provider_ids = [cred.provider_id for cred in credentials]
        providers = await ProviderService.get_providers_by_ids(provider_ids)
        provider_map = {str(provider.id): provider for provider in providers}

        credential_list = []
        for cred in credentials:
            provider = provider_map.get(str(cred.provider_id))
            if provider:
                # If task_type is specified, filter by provider.support
                if task_type is not None and (not provider.support or task_type not in provider.support):
                    continue
                usage_count = await self.model_crud.count_credential_usage(cred.id)
                decrypted_key = self._decrypt_api_key(cred.api_key)
                credential_list.append(CredentialDetail(
                    id=str(cred.id),
                    name=cred.name,
                    provider_id=cred.provider_id,
                    provider=provider.provider if provider else None,
                    provider_name=provider.name if provider else None,
                    base_url=cred.base_url,
                    additional_headers=cred.additional_headers,
                    is_active=cred.is_active,
                    created_at=cred.created_at,
                    updated_at=cred.updated_at,
                    api_key=decrypted_key,
                    usage_count=usage_count
                ))

        total = await self.crud.count_by_owner(owner_id)

        return CredentialList(
            credentials=credential_list,
            total=total,
            skip=skip,
            limit=limit
        )

    async def get_credential(self, owner_id: str, credential_id: str) -> CredentialDetail:
        """Get credential by ID with masked API key"""
        db_credential = await self.crud.get_by_owner_and_id(owner_id, credential_id)
        if not db_credential:
            raise AppError(
                message="Credential not found",
                status_code=404
            )

        # Get provider information
        provider = await ProviderService.get_provider_by_id(db_credential.provider_id)
        usage_count = await self.model_crud.count_credential_usage(db_credential.id)
        # Decrypt and mask the API key
        decrypted_key = self._decrypt_api_key(db_credential.api_key)
        # masked_key = self._mask_api_key(decrypted_key)

        return CredentialDetail(
            id=str(db_credential.id),
            name=db_credential.name,
            provider_id=db_credential.provider_id,
            provider_name=provider.name if provider else None,
            provider=provider.provider if provider else None,
            base_url=db_credential.base_url,
            additional_headers=db_credential.additional_headers,
            is_active=db_credential.is_active,
            created_at=db_credential.created_at,
            updated_at=db_credential.updated_at,
            api_key=decrypted_key,
            usage_count=usage_count
        )

    async def update_credential(self, owner_id: str, credential_id: str, update_data: CredentialUpdate):
        """Update credential"""
        db_credential = await self.crud.get_by_owner_and_id(owner_id, credential_id)
        if not db_credential:
            return False

        usage_count = await self.model_crud.count_credential_usage(db_credential.id)

        # If credential is being used by at least one model then cannot disable it
        update_dict = update_data.model_dump(exclude_none=True)
        if usage_count > 0 and 'is_active' in update_dict and update_dict['is_active'] is False:
            raise ValueError("Cannot disable credential that is being used by at least one model.")

        # Test API key and base URL if they are being updated
        if 'api_key' in update_dict or 'base_url' in update_dict:
            # Get provider information for validation
            provider = await ProviderService.get_provider_by_id(db_credential.provider_id)
            if not provider:
                raise ValueError(f"Provider with ID '{db_credential.provider_id}' not found or inactive")

            # Use new values or fall back to existing ones
            test_api_key = update_dict.get('api_key', self._decrypt_api_key(db_credential.api_key))
            test_base_url = update_dict.get('base_url', db_credential.base_url or provider.base_url)

            # Test the API key before updating the credential
            test_result = await self.verify_credential(
                provider=provider.provider,
                api_key=test_api_key,
                base_url=test_base_url
            )

            if not test_result.get('is_valid', False):
                error_msg = test_result.get('message', 'Invalid API key')
                error_details = test_result.get('error_details', '')
                full_error = f"{error_msg}. {error_details}" if error_details else error_msg
                raise ValueError(f"API key validation failed: {full_error}")

        # Encrypt API key if being updated
        if 'api_key' in update_dict:
            update_dict['api_key'] = self._encrypt_api_key(update_dict['api_key'])

        updated_credential = await self.crud.update(db_credential, update_dict)
        if not updated_credential:
            return None

        return updated_credential

    async def delete_credential(self, owner_id: str, credential_id: str):
        """Delete credential (soft delete)"""
        db_credential = await self.crud.get_by_owner_and_id(owner_id, credential_id)
        if not db_credential:
            return False

        await self.crud.soft_delete(db_credential, soft_delete=True)
        return db_credential

    async def get_providers(self, active_only: bool = True) -> ProviderList:
        """Get all AI providers"""
        providers = await ProviderService.get_all_providers(active_only)

        provider_list = [
            ProviderResponse(
                id=str(provider.id),
                provider=provider.provider,
                name=provider.name,
                description=provider.description,
                base_url=provider.base_url,
                logo_url=provider.logo_url,
                docs_url=provider.docs_url,
                api_key_header=provider.api_key_header,
                api_key_prefix=provider.api_key_prefix,
                is_active=provider.is_active,
                support=provider.support,
                tags=provider.tags,
                created_at=provider.created_at,
                updated_at=provider.updated_at
            )
            for provider in providers
        ]

        return ProviderList(
            providers=provider_list,
            total=len(provider_list)
        )


    def _parse_cached_model_data(self, cached_data: Any) -> List[ModelCredentialResponse]:
        """Parse cached model data and return list of ModelCredentialResponse"""
        try:
            if isinstance(cached_data, list):
                return [ModelCredentialResponse.model_validate(model) for model in cached_data]
            elif isinstance(cached_data, dict) and "data" in cached_data:
                return [ModelCredentialResponse.model_validate(model) for model in cached_data["data"]]
            else:
                return [ModelCredentialResponse.model_validate(cached_data)]
        except Exception as e:
            logger.error(f"Failed to parse cached model data: {e}")
            return []

    async def get_model_credential(self, owner_id: str, credential_id: str) -> List[ModelCredentialResponse]:
        """Get model credential, use cache if available"""
        credential = await self.crud.get_by_owner_and_id(owner_id, credential_id)

        if not credential:
            raise AppError(message="Credential not found", status_code=404)

        provider = await ProviderService.get_provider_by_id(credential.provider_id)
        data = await redis_service.jget(f"provider:{provider.provider}")
        if data:
            return self._parse_cached_model_data(data)

        # If cache is not available, use the existing verification function
        api_key = self._decrypt_api_key(credential.api_key)
        success, error_message = await self._verify_and_get_model_credential(
            base_url=credential.base_url,
            api_key=api_key,
            provider=provider.provider
        )

        if not success:
            raise AppError(message=f"Failed to get model credential: {error_message}", status_code=400)

        # Get the cached data after verification
        cached_data = await redis_service.jget(f"provider:{provider.provider}")
        if cached_data:
            return self._parse_cached_model_data(cached_data)

        return []


credential_service = CredentialService()
