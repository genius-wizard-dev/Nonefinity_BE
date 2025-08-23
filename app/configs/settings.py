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

class AuthSettings(BaseSettings):
    AUTH_JWT_ISS: str = "http://127.0.0.1:8000"
    AUTH_JWT_AUD: str = ""
    AUTH_JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AUTH_")

class Settings(AppSettings, MongoSettings, RedisSettings, SentrySettings, QdrantSettings, AuthSettings):
    RELEASE: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()