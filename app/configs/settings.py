from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    APP_NAME: str = "Nonefinity Agent"
    APP_ENV: Literal["dev", "prod"] = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

class CORSSettings(BaseSettings):
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

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
        if self.MONGO_USER and self.MONGO_PWD:
            return f"mongodb://{self.MONGO_USER}:{self.MONGO_PWD}@{self.MONGO_HOST}:{self.MONGO_PORT}"
        else:
            return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}"

class RedisSettings(BaseSettings):
    REDIS_HOST: str = ""
    REDIS_PORT: int = 6379
    REDIS_PWD: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="REDIS_")

class SentrySettings(BaseSettings):
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.2
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0
    SENTRY_SEND_DEFAULT_PII: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTRY_")

class QdrantSettings(BaseSettings):
    QDRANT_URL: str = ""

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

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DUCKDB_")


class PostgresSettings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env", env_prefix="POSTGRES_")

class Settings(AppSettings, CORSSettings, MongoSettings, RedisSettings, SentrySettings, QdrantSettings, ClerkSettings, MinioSettings, DuckDBSettings, PostgresSettings):
    RELEASE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()
