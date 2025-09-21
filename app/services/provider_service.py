import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.models.provider import Provider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ProviderService:
    """Enhanced service for managing AI providers with optimized MongoDB operations"""

    @staticmethod
    def load_providers_from_yaml(yaml_path: str = None) -> Dict:
        """Load providers configuration from YAML file"""
        if yaml_path is None:
            # Default path relative to the project root
            yaml_path = Path(__file__).parent.parent / "configs" / "providers.yaml"

        try:
            with open(yaml_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                return config.get('providers', {})
        except FileNotFoundError:
            logger.error(f"Provider configuration file not found: {yaml_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading providers: {e}")
            raise

    @staticmethod
    def _prepare_provider_data(provider_key: str, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare provider data from YAML format to match MongoDB model"""
        prepared_data = {
            'provider': provider_data.get('provider', provider_key),  # Use 'provider' field or fallback to key
            'name': provider_data['name'],
            'description': provider_data.get('description'),
            'base_url': provider_data['base_url'],
            'logo_url': provider_data.get('logo_url'),
            'docs_url': provider_data.get('docs_url'),
            'api_key_header': provider_data.get('api_key_header', 'Authorization'),
            'api_key_prefix': provider_data.get('api_key_prefix', 'Bearer'),
            'is_active': provider_data.get('is_active', True),
            'support': provider_data.get('support', []),
            'tasks': provider_data.get('tasks', {}),
            'tags': []  # Can be added later for categorization
        }

        # Remove None values to keep the document clean
        return {k: v for k, v in prepared_data.items() if v is not None}

    @staticmethod
    async def initialize_providers() -> int:
        """Load providers from YAML and save to MongoDB with enhanced error handling"""
        try:
            providers_config = ProviderService.load_providers_from_yaml()
            created_count = 0
            updated_count = 0
            error_count = 0

            # Process providers in batch for better performance
            for provider_key, provider_data in providers_config.items():
                try:
                    # Prepare data according to new model structure
                    prepared_data = ProviderService._prepare_provider_data(provider_key, provider_data)

                    # Check if provider already exists
                    existing_provider = await Provider.find_one(
                        Provider.provider == prepared_data['provider']
                    )

                    if existing_provider:
                        # Update existing provider with new fields
                        for key, value in prepared_data.items():
                            setattr(existing_provider, key, value)

                        # Validate before saving
                        await existing_provider.validate_self()
                        await existing_provider.save()
                        updated_count += 1
                        logger.info(f"Updated provider: {prepared_data['name']} ({prepared_data['provider']})")
                    else:
                        # Create new provider
                        provider = Provider(**prepared_data)
                        await provider.insert()
                        created_count += 1
                        logger.info(f"Created provider: {prepared_data['name']} ({prepared_data['provider']})")

                except Exception as provider_error:
                    error_count += 1
                    logger.error(f"Failed to process provider {provider_key}: {provider_error}")
                    continue

            total_processed = created_count + updated_count
            logger.info(f"Provider initialization completed. Created: {created_count}, Updated: {updated_count}, Errors: {error_count}")

            if error_count > 0:
                logger.warning("Some providers failed to initialize. Check logs for details.")

            return total_processed

        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
            raise

    @staticmethod
    async def get_all_providers(active_only: bool = True) -> List[Provider]:
        """Get all providers from database with optimized queries"""
        if active_only:
            providers = await Provider.find({"is_active": True}).to_list()
        else:
            providers = await Provider.find_all().to_list()

        logger.debug(f"Retrieved {len(providers)} providers (active_only={active_only})")
        return providers

    @staticmethod
    async def get_provider_by_name(provider_name: str, active_only: bool = True) -> Provider:
        """Get a specific provider by name with enhanced error handling"""
        query = {"provider": provider_name}
        if active_only:
            query["is_active"] = True

        provider = await Provider.find_one(query)
        if not provider:
            status_msg = "not found or inactive" if active_only else "not found"
            raise ValueError(f"Provider '{provider_name}' {status_msg}")
        return provider

    @staticmethod
    async def get_provider_by_id(provider_id: str, active_only: bool = True) -> Optional[Provider]:
        """Get a specific provider by ID"""
        from bson import ObjectId
        query = {"_id": ObjectId(provider_id)}
        if active_only:
            query["is_active"] = True

        provider = await Provider.find_one(query)
        return provider

    @staticmethod
    async def get_providers_by_task(task_type: str, active_only: bool = True) -> List[Provider]:
        """Get providers that support a specific task type"""
        query = {"support": {"$in": [task_type]}}
        if active_only:
            query["is_active"] = True

        providers = await Provider.find(query).to_list()
        logger.debug(f"Found {len(providers)} providers supporting '{task_type}' task")
        return providers

    @staticmethod
    async def get_provider_task_config(provider_name: str, task_type: str) -> Optional[Dict[str, Any]]:
        """Get task configuration for a specific provider and task type"""
        provider = await ProviderService.get_provider_by_name(provider_name)

        if not provider.supports_task(task_type):
            raise ValueError(f"Provider '{provider_name}' does not support '{task_type}' task")

        return provider.get_task_config(task_type)

    @staticmethod
    async def refresh_providers() -> int:
        """Refresh providers from YAML file"""
        logger.info("Refreshing providers from configuration file...")
        return await ProviderService.initialize_providers()

    @staticmethod
    async def deactivate_provider(provider_name: str) -> bool:
        """Deactivate a provider"""
        provider = await ProviderService.get_provider_by_name(provider_name, active_only=False)
        provider.is_active = False
        await provider.save()
        logger.info(f"Deactivated provider: {provider_name}")
        return True

    @staticmethod
    async def activate_provider(provider_name: str) -> bool:
        """Activate a provider"""
        provider = await ProviderService.get_provider_by_name(provider_name, active_only=False)
        provider.is_active = True
        await provider.save()
        logger.info(f"Activated provider: {provider_name}")
        return True

    @staticmethod
    async def update_provider_config(provider_name: str, updates: Dict[str, Any]) -> Provider:
        """Update provider configuration"""
        provider = await ProviderService.get_provider_by_name(provider_name, active_only=False)

        # Update allowed fields
        allowed_fields = {
            'name', 'description', 'base_url', 'logo_url', 'docs_url',
            'api_key_header', 'api_key_prefix', 'is_active', 'support',
            'tasks', 'provider_type', 'tags'
        }

        for key, value in updates.items():
            if key in allowed_fields:
                setattr(provider, key, value)

        await provider.validate_self()
        await provider.save()
        logger.info(f"Updated provider configuration: {provider_name}")
        return provider
