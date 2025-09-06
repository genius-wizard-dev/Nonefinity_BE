from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    APP_NAME: str = "Nonefinity Agent"
    APP_ENV: Literal["dev", "prod"] = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

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
    REDIS_URL: str = ""
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
    JWT_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env")

class MinioSettings(BaseSettings):
    MINIO_URL: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_ALIAS: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MINIO_")


class Settings(AppSettings, MongoSettings, RedisSettings, SentrySettings, QdrantSettings, ClerkSettings, MinioSettings):
    RELEASE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()
