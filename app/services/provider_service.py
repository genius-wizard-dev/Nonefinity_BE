import os
import yaml
from typing import Dict, List
from pathlib import Path

from app.models.credential import Provider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ProviderService:
    """Service for managing AI providers"""

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
    async def initialize_providers() -> int:
        """Load providers from YAML and save to MongoDB"""
        try:
            providers_config = ProviderService.load_providers_from_yaml()
            created_count = 0
            updated_count = 0

            for provider_key, provider_data in providers_config.items():
                # Check if provider already exists
                existing_provider = await Provider.find_one(
                    Provider.provider_name == provider_data['provider_name']
                )

                if existing_provider:
                    # Update existing provider
                    for key, value in provider_data.items():
                        setattr(existing_provider, key, value)
                    await existing_provider.save()
                    updated_count += 1
                    logger.info(f"Updated provider: {provider_data['name']}")
                else:
                    # Create new provider
                    provider = Provider(**provider_data)
                    await provider.insert()
                    created_count += 1
                    logger.info(f"Created provider: {provider_data['name']}")

            total_processed = created_count + updated_count
            logger.info(f"Provider initialization completed. Created: {created_count}, Updated: {updated_count}")
            return total_processed

        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
            raise

    @staticmethod
    async def get_all_providers(active_only: bool = True) -> List[Provider]:
        """Get all providers from database"""
        query = Provider.find()
        if active_only:
            query = Provider.find(Provider.is_active == True)

        providers = await query.to_list()
        return providers

    @staticmethod
    async def get_provider_by_name(provider_name: str) -> Provider:
        """Get a specific provider by name"""
        provider = await Provider.find_one(
            Provider.provider_name == provider_name,
            Provider.is_active == True
        )
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found or inactive")
        return provider

    @staticmethod
    async def refresh_providers() -> int:
        """Refresh providers from YAML file"""
        logger.info("Refreshing providers from configuration file...")
        return await ProviderService.initialize_providers()
