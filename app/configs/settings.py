from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    APP_NAME: str = "Nonefinity Agent"
    APP_ENV: Literal["dev", "prod"] = "dev"
    APP_DEBUG: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")


class CORSSettings(BaseSettings):
    CORS_ORIGINS: list[str] = ["https://nonefinity.com",
                               "http://127.0.0.1:5173", "http://localhost:5173"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]
    CORS_EXPOSE_HEADERS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CORS_")


class MongoSettings(BaseSettings):
    MONGO_HOST: str = ""
    MONGO_PORT: int = 27017
    MONGO_DB: str = ""
    MONGO_USER: str = ""
    MONGO_PWD: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MONGO_")

    @property
    def MONGO_URL(self) -> str:
        host = self.MONGO_HOST or "localhost"
        port = self.MONGO_PORT or 27017
        if self.MONGO_USER and self.MONGO_PWD:
            return f"mongodb://{self.MONGO_USER}:{self.MONGO_PWD}@{host}:{port}"
        return f"mongodb://{host}:{port}"


class RedisSettings(BaseSettings):
    REDIS_HOST: str = ""
    REDIS_PORT: int = 6379
    REDIS_PWD: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="REDIS_")

    @property
    def redis_password(self) -> str:
        return self.REDIS_PWD


class CelerySettings(BaseSettings):
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CELERY_")

    @property
    def get_broker_url(self) -> str:
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        from app.configs.settings import settings
        pwd = settings.redis_password
        if pwd:
            return f"redis://:{pwd}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
        return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"

    @property
    def get_result_backend(self) -> str:
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        from app.configs.settings import settings
        pwd = settings.redis_password
        if pwd:
            return f"redis://:{pwd}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
        return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"


class SentrySettings(BaseSettings):
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.2
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0
    SENTRY_SEND_DEFAULT_PII: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTRY_")


class QdrantSettings(BaseSettings):
    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="QDRANT_")


class ClerkSettings(BaseSettings):
    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""
    CLERK_ISSUER: str = ""
    CLERK_JWKS_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env")


class MinioSettings(BaseSettings):
    MINIO_URL: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_ALIAS: str = ""

    @property
    def MINIO_SSL(self) -> bool:
        return self.MINIO_URL.startswith("https://")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MINIO_")


class DuckDBSettings(BaseSettings):
    DUCKDB_TEMP_FOLDER: str
    DUCKDB_INSTANCE_TTL: int = 600
    DUCKDB_CLEANUP_INTERVAL: int = 300
    DUCKDB_CONNECTION_POOL_SIZE: int = 3
    DUCKDB_QUERY_TIMEOUT: int = 30
    DUCKDB_THREAD_POOL_SIZE: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DUCKDB_")


class PostgresSettings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env", env_prefix="POSTGRES_")


class CredentialSettings(BaseSettings):
    CREDENTIAL_SECRET_KEY: str
    CREDENTIAL_ENCRYPTION_SALT: str
    CREDENTIAL_KDF_ITERATIONS: int = 100000

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="CREDENTIAL_")


class ComposioSettings(BaseSettings):
    COMPOSIO_API_KEY: str
    COMPOSIO_WEBHOOK_SECRET: str

    model_config = SettingsConfigDict(env_file=".env", env_prefix="COMPOSIO_")


class OpenAISettings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPENAI_")


class Settings(AppSettings, CORSSettings, MongoSettings, RedisSettings, CelerySettings, SentrySettings, QdrantSettings, ClerkSettings, MinioSettings, DuckDBSettings, PostgresSettings, CredentialSettings, ComposioSettings, OpenAISettings):
    RELEASE: str | None = None
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()
