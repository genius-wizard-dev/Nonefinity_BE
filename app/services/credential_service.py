import base64
import aiohttp
import secrets
from datetime import datetime
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import InvalidToken

from app.crud.credential import CredentialCRUD
from app.crud.model import ModelCRUD
from app.schemas.credential import (
    CredentialCreate, CredentialUpdate, Credential, CredentialDetail,
    CredentialList
)
from app.schemas.provider import ProviderResponse, ProviderList
from app.services.provider_service import ProviderService
from app.configs.settings import settings
from app.core.exceptions import AppError
from app.schemas.model import ModelType
from app.utils import get_logger

logger = get_logger(__name__)


class CredentialService:
    def __init__(self, crud: Optional[CredentialCRUD] = None):
        self.crud = crud or CredentialCRUD()
        self.model_crud = ModelCRUD()
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



    # def _mask_api_key(self, api_key: str) -> str:
    #     """Mask API key, show first 6 chars, rest as a few • (not too long)"""
    #     s = str(api_key or "")
    #     if len(s) <= 6:
    #         return "•" * len(s)
    #     # Show first 6, then 4 * only, regardless of length
    #     return s[:6] + "•" * 10

    @staticmethod
    def generate_secure_key(length: int = 32) -> str:
        """Generate a cryptographically secure random key"""
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('utf-8')

    def validate_encryption_health(self) -> Dict[str, Any]:
        """Validate that encryption/decryption is working properly"""
        try:
            test_data = "test-encryption-health-check"
            encrypted = self._encrypt_api_key(test_data)
            decrypted = self._decrypt_api_key(encrypted)

            is_healthy = (decrypted == test_data)

            return {
                "encryption_healthy": is_healthy,
                "test_passed": is_healthy,
                "encryption_algorithm": "Fernet (AES 128)",
                "kdf_iterations": settings.CREDENTIAL_KDF_ITERATIONS,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Encryption health check failed: {e}")
            return {
                "encryption_healthy": False,
                "test_passed": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def create_credential(self, owner_id: str, credential_data: CredentialCreate) -> bool:
        """Create a new credential with API key validation, return bool indicating success"""
        # Get provider information first for validation
        provider = await ProviderService.get_provider_by_id(credential_data.provider_id)
        if not provider:
            raise ValueError(f"Provider with ID '{credential_data.provider_id}' not found or inactive")

        # Auto-fill base_url from provider if not provided
        if not credential_data.base_url:
            credential_data.base_url = provider.base_url

        # Test the API key before creating the credential
        test_result = await self.verify_credential(
            provider=provider.provider,
            api_key=credential_data.api_key,
            base_url=credential_data.base_url
        )

        if not test_result.get('is_valid', False):
            error_msg = test_result.get('message', 'Invalid API key')
            error_details = test_result.get('error_details', '')
            full_error = f"{error_msg}. {error_details}" if error_details else error_msg
            raise ValueError(f"API key validation failed: {full_error}")

        # Encrypt the API key before saving
        encrypted_data = credential_data.model_copy()
        encrypted_data.api_key = self._encrypt_api_key(credential_data.api_key)

        try:
            db_credential = await self.crud.create_with_owner(owner_id, encrypted_data)
            if db_credential:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Failed to create credential: {e}")
            return False

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
            page=skip // limit + 1 if limit > 0 else 1,
            size=limit
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
            base_url=db_credential.base_url,
            additional_headers=db_credential.additional_headers,
            is_active=db_credential.is_active,
            created_at=db_credential.created_at,
            updated_at=db_credential.updated_at,
            api_key=decrypted_key,
            usage_count=usage_count
        )

    async def update_credential(self, owner_id: str, credential_id: str, update_data: CredentialUpdate) -> bool:
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
            return False

        return True

    async def delete_credential(self, owner_id: str, credential_id: str) -> bool:
        """Delete credential (soft delete)"""
        db_credential = await self.crud.get_by_owner_and_id(owner_id, credential_id)
        if not db_credential:
            return False

        await self.crud.soft_delete(db_credential, soft_delete=True)
        return True

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
                tasks=provider.tasks,
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

    async def verify_credential(
        self,
        owner_id: Optional[str] = None,
        credential_id: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test a credential by making a simple API call"""
        start_time = datetime.utcnow()

        try:
            # Get credential details
            if credential_id and owner_id:
                db_credential = await self.crud.get_by_owner_and_id(owner_id, credential_id)
                if not db_credential:
                    return {
                        'is_valid': False,
                        'message': 'Credential not found',
                        'error_details': 'The specified credential does not exist'
                    }

                test_api_key = self._decrypt_api_key(db_credential.api_key)
                verify_provider = await ProviderService.get_provider_by_id(db_credential.provider_id)
                test_base_url = db_credential.base_url or verify_provider.base_url
            else:
                # Ad-hoc testing
                if not provider or not api_key:
                    return {
                        'is_valid': False,
                        'message': 'Missing required parameters',
                        'error_details': 'Provider name and API key are required'
                    }

                verify_provider = await ProviderService.get_provider_by_name(provider)
                test_api_key = api_key
                test_base_url = base_url or verify_provider.base_url

            # Prepare test request
            headers = {
                verify_provider.api_key_header: f"{verify_provider.api_key_prefix} {test_api_key}".strip(),
                'Content-Type': 'application/json'
            }

            # Choose test endpoint based on provider
            test_url = f"{test_base_url}/models"

            # Make test request
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(test_url, headers=headers) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        return {
                            'is_valid': True,
                            'message': 'Credential is valid and working',
                            'response_time_ms': int(response_time)
                        }
                    elif response.status == 401:
                        return {
                            'is_valid': False,
                            'message': 'Invalid API key',
                            'response_time_ms': int(response_time),
                            'error_details': 'The API key is invalid or expired'
                        }
                    elif response.status == 403:
                        return {
                            'is_valid': False,
                            'message': 'Access forbidden',
                            'response_time_ms': int(response_time),
                            'error_details': 'The API key does not have permission'
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'is_valid': False,
                            'message': f'API returned status {response.status}',
                            'response_time_ms': int(response_time),
                            'error_details': error_text[:200] if error_text else 'Unknown error'
                        }

        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Error testing credential: {e}")
            return {
                'is_valid': False,
                'message': 'Test failed',
                'response_time_ms': int(response_time),
                'error_details': str(e)
            }


credential_service = CredentialService()
